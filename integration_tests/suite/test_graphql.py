# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    any_of,
    assert_that,
    contains,
    contains_string,
    equal_to,
    has_entries,
    has_entry,
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
            metadata={'uuid': 'my-user-uuid', 'tenant_uuid': MAIN_TENANT}
        )
        mock_auth_client.set_token(main_tenant_token)
        cls.main_tenant_token = main_tenant_token.token_id
        cls.dird = DirdClient(
            'localhost', cls.service_port(9489, 'dird'), verify_certificate=False
        )
        cls.dird.set_token(cls.main_tenant_token)

    def test_authentication(self):
        dird = DirdClient(
            'localhost', self.service_port(9489, 'dird'), verify_certificate=False
        )
        query = {'query': '{ hello }'}

        # Wrong token
        dird.set_token(None)
        response = dird.graphql.query(query)
        assert_that(
            response['errors'],
            contains(
                has_entries(
                    {
                        'path': ['hello'],
                        'message': 'Unauthorized',
                        'extensions': has_entry('error_id', 'unauthorized'),
                    }
                )
            ),
        )

        # Token without ACL
        dird.set_token(VALID_TOKEN_NO_ACL)
        response = dird.graphql.query(query)
        assert_that(
            response['errors'],
            contains(
                has_entries(
                    {
                        'path': ['hello'],
                        'message': 'Unauthorized',
                        'extensions': has_entry('error_id', 'unauthorized'),
                    }
                )
            ),
        )

        # Valid token
        dird.set_token(VALID_TOKEN)
        response = dird.graphql.query(query)
        assert response == {'data': {'hello': 'world'}}

    def test_hello_world(self):
        query = {'query': '{ hello }'}

        response = self.dird.graphql.query(query)

        assert response == {'data': {'hello': 'world'}}

    def test_user_me(self):
        query = {
            'query': '''
            {
                me {
                    userUuid
                }
            }
            ''',
        }

        response = self.dird.graphql.query(query)

        assert_that(response['data']['me']['userUuid'], equal_to('my-user-uuid'))

    def test_multiple_reverse_lookup(self):
        query = {
            'query': '''
            {
                me {
                    contacts(profile: "default", extens: ["5555555555", "5555551234"]) {
                        edges {
                            node {
                                firstname
                            }
                        }
                    }
                }
            }
            ''',
        }

        response = self.dird.graphql.query(query)

        assert_that(
            response['data']['me']['contacts']['edges'],
            contains(
                has_entry('node', has_entries({'firstname': 'Alice'})),
                has_entry('node', has_entries({'firstname': 'Bob'})),
            ),
        )

    def test_multiple_reverse_lookup_wrong_profile(self):
        query = {
            'query': '''
            {
                me {
                    contacts(profile: "wrong", extens: ["5555555555", "5555551234"]) {
                        edges {
                            node {
                                firstname
                            }
                        }
                    }
                }
            }
            ''',
        }

        response = self.dird.graphql.query(query)

        assert_that(
            response['errors'],
            contains(
                has_entries(
                    {
                        'path': ['me', 'contacts'],
                        'message': contains_string('profile'),
                        'extensions': has_entry('error_id', 'unknown-profile'),
                    }
                )
            ),
        )

    def test_multiple_reverse_lookup_with_one_error(self):
        query = {
            'query': '''
            {
                me {
                    contacts(profile: "default", extens: ["5555555555", "999", "5555551234"]) {
                        edges {
                            node {
                                firstname
                            }
                        }
                    }
                }
            }
            ''',
        }

        response = self.dird.graphql.query(query)

        assert_that(
            response['data']['me']['contacts']['edges'],
            contains(
                has_entry('node', has_entries({'firstname': 'Alice'})),
                has_entry('node', None),
                has_entry('node', has_entries({'firstname': 'Bob'})),
            ),
        )

    def test_multiple_reverse_contact_fields(self):
        query = {
            'query': '''
            {
                me {
                    contacts(profile: "default", extens: ["5555555555"]) {
                        edges {
                            node {
                                firstname
                                lastname
                                wazoReverse
                                wazoSourceName
                            }
                        }
                    }
                }
            }
            ''',
        }

        response = self.dird.graphql.query(query)

        assert_that(
            response['data']['me']['contacts']['edges'],
            contains(
                has_entry(
                    'node',
                    has_entries(
                        {
                            'firstname': 'Alice',
                            'lastname': 'AAA',
                            'wazoReverse': 'Alice AAA',
                            'wazoSourceName': any_of('my_csv', 'my_csv_2'),
                        }
                    ),
                ),
            ),
        )


class TestGraphQLNoAuth(BaseDirdIntegrationTest):

    asset = 'no_auth_server'

    def test_unreachable_auth_should_return_error(self):
        dird = DirdClient(
            'localhost', self.service_port(9489, 'dird'), verify_certificate=False
        )
        dird.set_token(VALID_TOKEN)
        query = {'query': '{ hello }'}

        response = dird.graphql.query(query)
        assert_that(
            response['errors'],
            contains(
                has_entries(
                    {'path': ['hello'], 'message': contains_string('unreachable')}
                )
            ),
        )
