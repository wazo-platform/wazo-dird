# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    contains,
    contains_string,
    equal_to,
    has_entries,
)
from wazo_dird_client import Client as DirdClient
from xivo_test_helpers.auth import AuthClient as MockAuthClient, MockUserToken

from .helpers.base import BaseDirdIntegrationTest
from .helpers.config import new_csv_with_multiple_displays_config
from .helpers.constants import VALID_TOKEN, VALID_TOKEN_NO_ACL, MAIN_TENANT


class TestGraphQL(BaseDirdIntegrationTest):

    asset = 'all_routes'
    config_factory = new_csv_with_multiple_displays_config

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        mock_auth_client = MockAuthClient('localhost', cls.service_port(9497, 'auth'))
        main_tenant_token = MockUserToken.some_token(
            metadata={'tenant_uuid': MAIN_TENANT}
        )
        mock_auth_client.set_token(main_tenant_token)
        cls.main_tenant_token = main_tenant_token.token_id

    def test_authentication(self):
        dird = DirdClient(
            'localhost', self.service_port(9489, 'dird'), verify_certificate=False
        )
        query = {'query': '{ hello }'}
        tenant_uuid = None
        token = None

        # Wrong token
        response = dird.graphql.query(query, tenant_uuid, token)
        assert_that(
            response['errors'],
            contains(has_entries({'path': ['hello'], 'message': 'Unauthorized'})),
        )

        # Token without ACL
        response = dird.graphql.query(query, tenant_uuid, VALID_TOKEN_NO_ACL)
        assert_that(
            response['errors'],
            contains(has_entries({'path': ['hello'], 'message': 'Unauthorized'})),
        )

        # Valid token
        response = dird.graphql.query(query, tenant_uuid, VALID_TOKEN)
        assert response == {'data': {'hello': 'world'}}

    def test_hello_world(self):
        dird = DirdClient(
            'localhost', self.service_port(9489, 'dird'), verify_certificate=False
        )
        query = {'query': '{ hello }'}
        tenant_uuid = None

        response = dird.graphql.query(query, tenant_uuid, VALID_TOKEN)

        assert response == {'data': {'hello': 'world'}}

    def test_user_me(self):
        dird = DirdClient(
            'localhost', self.service_port(9489, 'dird'), verify_certificate=False
        )
        tenant_uuid = None
        query = {
            'query': '''
            {
                me {
                    user_uuid
                }
            }
            ''',
        }

        response = dird.graphql.query(query, tenant_uuid, VALID_TOKEN)

        assert_that(response['data']['me']['user_uuid'], equal_to('uuid'))

    def test_multiple_reverse_lookup(self):
        dird = DirdClient(
            'localhost', self.service_port(9489, 'dird'), verify_certificate=False
        )
        tenant_uuid = None
        query = {
            'query': '''
            {
                me {
                    contacts(profile: "default", extens: ["5555555555", "5555551234"]) {
                        firstname
                    }
                }
            }
            ''',
        }

        response = dird.graphql.query(query, tenant_uuid, self.main_tenant_token)

        assert_that(
            response['data']['me']['contacts'],
            contains(
                has_entries({'firstname': 'Alice'}), has_entries({'firstname': 'Bob'}),
            ),
        )

    def test_multiple_reverse_lookup_wrong_profile(self):
        dird = DirdClient(
            'localhost', self.service_port(9489, 'dird'), verify_certificate=False
        )
        tenant_uuid = None
        query = {
            'query': '''
            {
                me {
                    contacts(profile: "wrong", extens: ["5555555555", "5555551234"]) {
                        firstname
                    }
                }
            }
            ''',
        }

        response = dird.graphql.query(query, tenant_uuid, self.main_tenant_token)

        assert_that(
            response['errors'],
            contains(
                has_entries(
                    {'path': ['me', 'contacts'], 'message': contains_string('profile')}
                )
            ),
        )

    def test_multiple_reverse_lookup_with_one_error(self):
        dird = DirdClient(
            'localhost', self.service_port(9489, 'dird'), verify_certificate=False
        )
        tenant_uuid = None
        query = {
            'query': '''
            {
                me {
                    contacts(profile: "default", extens: ["5555555555", "999", "5555551234"]) {
                        firstname
                    }
                }
            }
            ''',
        }

        response = dird.graphql.query(query, tenant_uuid, self.main_tenant_token)

        assert_that(
            response['data']['me']['contacts'],
            contains(
                has_entries({'firstname': 'Alice'}),
                None,
                has_entries({'firstname': 'Bob'}),
            ),
        )


class TestGraphQLNoAuth(BaseDirdIntegrationTest):

    asset = 'no_auth_server'

    def test_unreachable_auth_should_return_error(self):
        dird = DirdClient(
            'localhost', self.service_port(9489, 'dird'), verify_certificate=False
        )
        query = {'query': '{ hello }'}
        tenant_uuid = None

        response = dird.graphql.query(query, tenant_uuid, VALID_TOKEN)
        assert_that(
            response['errors'],
            contains(
                has_entries(
                    {'path': ['hello'], 'message': contains_string('unreachable')}
                )
            ),
        )
