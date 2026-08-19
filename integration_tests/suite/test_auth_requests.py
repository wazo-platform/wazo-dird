# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import ClassVar

from hamcrest import assert_that, equal_to, has_key, has_length, not_
from wazo_test_helpers.auth import AuthClient as MockAuthClient
from wazo_test_helpers.auth import MockUserToken

from .helpers.base import BaseDirdIntegrationTest
from .helpers.config import new_csv_with_multiple_displays_config
from .helpers.constants import MAIN_TENANT

USER_UUID = 'my-user-uuid'


class TestTokenRequestCount(BaseDirdIntegrationTest):
    '''wazo-dird must not fetch the same token from wazo-auth twice.

    The counts below are a budget: verify_token always costs one request,
    and the token itself is fetched at most once more, only when the user
    UUID or the tenant cannot be read from the request headers.
    '''

    asset = 'all_routes'
    config_factory = new_csv_with_multiple_displays_config

    auth: ClassVar[MockAuthClient]
    token: ClassVar[str]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.auth = MockAuthClient('127.0.0.1', cls.service_port(9497, 'auth'))
        token = MockUserToken.some_token(
            metadata={'uuid': USER_UUID, 'tenant_uuid': MAIN_TENANT}
        )
        cls.auth.set_token(token)
        cls.token = token.token_id

    def _count_token_requests(self, url, tenant=None, **kwargs):
        with self.auth.capture_requests() as capture:
            response = self.get(url, token=self.token, tenant=tenant, **kwargs)
        assert_that(response.status_code, equal_to(200))
        return [
            request
            for request in capture.requests
            if request['path'].startswith('/0.1/token')
            and request['method'] in ('GET', 'HEAD')
        ]

    def _count_graphql_token_requests(self, query, tenant=None):
        with self.auth.capture_requests() as capture:
            response = self.post(
                self.url('graphql'),
                json={'query': query},
                token=self.token,
                tenant=tenant,
            )
        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), not_(has_key('errors')))
        return [
            request
            for request in capture.requests
            if request['path'].startswith('/0.1/token')
            and request['method'] in ('GET', 'HEAD')
        ]

    def test_lookup(self):
        url = self.url('directories', 'lookup', 'default')
        params = {'term': 'alice'}

        requests = self._count_token_requests(url, params=params)
        assert_that(requests, has_length(2), 'the tenant comes from the token')

        requests = self._count_token_requests(url, tenant=MAIN_TENANT, params=params)
        assert_that(requests, has_length(2), 'the user UUID comes from the token')

    def test_lookup_by_user_uuid(self):
        url = self.url('directories', 'lookup', 'default', USER_UUID)
        params = {'term': 'alice'}

        requests = self._count_token_requests(url, params=params)
        assert_that(requests, has_length(2), 'the tenant comes from the token')

        requests = self._count_token_requests(url, tenant=MAIN_TENANT, params=params)
        assert_that(requests, has_length(1), 'nothing is read from the token')

    def test_reverse(self):
        url = self.url('directories', 'reverse', 'default', USER_UUID)
        params = {'exten': '1234'}

        requests = self._count_token_requests(url, params=params)
        assert_that(requests, has_length(2), 'the tenant comes from the token')

        requests = self._count_token_requests(url, tenant=MAIN_TENANT, params=params)
        assert_that(requests, has_length(1), 'nothing is read from the token')

    def test_favorites(self):
        url = self.url('directories', 'favorites', 'default')

        requests = self._count_token_requests(url)
        assert_that(requests, has_length(2), 'the tenant comes from the token')

        requests = self._count_token_requests(url, tenant=MAIN_TENANT)
        assert_that(requests, has_length(2), 'the user UUID comes from the token')

    def test_personal(self):
        url = self.url('personal')

        requests = self._count_token_requests(url)
        assert_that(requests, has_length(2), 'the user UUID comes from the token')

        requests = self._count_token_requests(url, tenant=MAIN_TENANT)
        assert_that(requests, has_length(2), 'the user UUID comes from the token')

    def test_graphql_user_me(self):
        query = '{ me { userUuid } }'

        requests = self._count_graphql_token_requests(query)
        assert_that(requests, has_length(2), 'the tenant comes from the token')

        requests = self._count_graphql_token_requests(query, tenant=MAIN_TENANT)
        assert_that(requests, has_length(3), 'the tenant is checked against the token')

    def test_graphql_user_me_contacts(self):
        query = '''
        {
            me {
                contacts(profile: "default", extens: ["1234"]) {
                    edges { node { firstname } }
                }
            }
        }
        '''

        requests = self._count_graphql_token_requests(query)
        assert_that(requests, has_length(2), 'the tenant comes from the token')

        requests = self._count_graphql_token_requests(query, tenant=MAIN_TENANT)
        assert_that(requests, has_length(3), 'the tenant is checked against the token')
