# Copyright 2020-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import contextmanager

from hamcrest import (
    any_of,
    assert_that,
    contains,
    contains_string,
    equal_to,
    has_entries,
    has_entry,
    has_key,
    not_,
)
from wazo_dird_client import Client as DirdClient
from wazo_test_helpers.auth import AuthClient as MockAuthClient
from wazo_test_helpers.auth import MockUserToken

from .helpers.base import BaseDirdIntegrationTest
from .helpers.config import new_csv_with_multiple_displays_config, new_wazo_users_config
from .helpers.constants import MAIN_TENANT, VALID_TOKEN, VALID_TOKEN_NO_ACL


class TestGraphQL(BaseDirdIntegrationTest):
    asset = 'all_routes'
    config_factory = new_csv_with_multiple_displays_config

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._configure_auth()

    @classmethod
    def _configure_auth(cls):
        cls.auth = MockAuthClient('127.0.0.1', cls.service_port(9497, 'auth'))
        main_tenant_token = MockUserToken.some_token(
            metadata={'uuid': 'my-user-uuid', 'tenant_uuid': MAIN_TENANT}
        )
        cls.auth.set_token(main_tenant_token)
        cls.main_tenant_token = main_tenant_token.token_id
        cls.dird = DirdClient(
            '127.0.0.1', cls.service_port(9489, 'dird'), prefix=None, https=False
        )
        cls.dird.set_token(cls.main_tenant_token)

    @classmethod
    @contextmanager
    def auth_stopped(cls):
        with super().auth_stopped():
            yield
        cls._configure_auth()

    def setUp(self):
        super().setUp()
        self.dird.set_token(self.main_tenant_token)

    def test_authentication(self):
        # Wrong token
        self.dird.set_token(None)
        query = {'query': '{ hello }'}
        response = self.dird.graphql.query(query)
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
        self.dird.set_token(VALID_TOKEN_NO_ACL)
        query = {'query': '{ hello }'}
        response = self.dird.graphql.query(query)
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

        # Valid token get subfield
        token = MockUserToken.some_token(
            user_uuid='my-user-uuid',
            metadata={'tenant_uuid': MAIN_TENANT},
            acl=['dird.graphql.me'],
        )
        self.auth.set_token(token)
        query = {'query': '{ me { userUuid } }'}
        self.dird.set_token(token.token_id)
        response = self.dird.graphql.query(query)
        assert response == {'data': {'me': {'userUuid': 'my-user-uuid'}}}

        # Valid token
        token = MockUserToken.some_token(
            user_uuid='my-user-uuid',
            metadata={'tenant_uuid': MAIN_TENANT},
            acl=['dird.graphql.hello'],
        )
        self.auth.set_token(token)
        self.dird.set_token(token.token_id)
        query = {'query': '{ hello }'}
        response = self.dird.graphql.query(query)
        assert response == {'data': {'hello': 'world'}}

        # No token needed for __schema
        self.dird.set_token(None)
        query = {'query': '{ __schema { queryType { name }}}'}
        response = self.dird.graphql.query(query)
        assert response == {'data': {'__schema': {'queryType': {'name': 'Query'}}}}

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

    def test_user_uuid(self):
        # use a sprecific uuid instead of "me"

        user_uuid = 'my-user-uuid'
        query = {
            'query': '''
            query GetUuidFromUser($uuid: String!) {
                 user(uuid: $uuid) {
                     uuid
                 }
            }
            ''',
            'variables': {'uuid': user_uuid},
        }

        response = self.dird.graphql.query(query)

        assert_that(response['data']['user']['uuid'], equal_to(user_uuid))

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
                                email
                                wazoReverse
                                wazoSourceName
                                wazoSourceEntryId
                                wazoBackend
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
                            'email': 'alice@example.com',
                            'wazoReverse': 'Alice AAA',
                            'wazoSourceName': any_of('my_csv', 'my_csv_2'),
                            'wazoSourceEntryId': '1',
                            'wazoBackend': 'csv',
                        }
                    ),
                ),
            ),
        )

    def test_reverse_missing_contact_fields(self):
        query = {
            'query': '''
            {
                me {
                    contacts(profile: "default", extens: ["4444444444"]) {
                        edges {
                            node {
                                firstname
                                lastname
                                email
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
                        {'firstname': 'Dave', 'lastname': 'DDD', 'email': None}
                    ),
                ),
            ),
        )
        assert_that(response, not_(has_key('errors')))

    def test_unreachable_auth_should_return_error(self):
        with self.auth_stopped():
            dird = self.make_dird(VALID_TOKEN)
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


class TestGraphQLWazoBackend(BaseDirdIntegrationTest):
    asset = 'wazo_users_multiple_wazo'
    config_factory = new_wazo_users_config

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.auth = MockAuthClient('127.0.0.1', cls.service_port(9497, 'auth'))
        main_tenant_token = MockUserToken.some_token(
            metadata={'uuid': 'my-user-uuid', 'tenant_uuid': MAIN_TENANT}
        )
        cls.auth.set_token(main_tenant_token)
        cls.main_tenant_token = main_tenant_token.token_id
        cls.dird = DirdClient(
            '127.0.0.1', cls.service_port(9489, 'dird'), prefix=None, https=False
        )
        cls.dird.set_token(cls.main_tenant_token)

    def setUp(self):
        super().setUp()
        self.dird.set_token(self.main_tenant_token)

    def test_wazo_backend_fields(self):
        query = {
            'query': '''
            {
                me {
                    contacts(profile: "default", extens: ["1234"]) {
                        edges {
                            node {
                                firstname
                                lastname
                                ... on WazoContact {
                                    userUuid,
                                    userId,
                                    agentId,
                                    endpointId
                                }
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
                            'firstname': 'John',
                            'lastname': 'Doe',
                            'userUuid': '7ca42f43-8bd9-4a26-acb8-cb756f42bebb',
                            'userId': '1',
                            'agentId': '3',
                            'endpointId': '2',
                        }
                    ),
                ),
            ),
        )
