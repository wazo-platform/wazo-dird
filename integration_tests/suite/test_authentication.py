# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, contains_string, equal_to

from .helpers.base import BaseDirdIntegrationTest
from .helpers.config import new_auth_only_config
from .helpers.constants import VALID_TOKEN_MAIN_TENANT, VALID_TOKEN_NO_ACL, VALID_UUID


class TestAuthentication(BaseDirdIntegrationTest):

    asset = 'all_routes'
    config_factory = new_auth_only_config

    def test_no_auth_gives_401(self):
        result = self.get_headers_result('default', token=None)

        assert_that(result.status_code, equal_to(401))

    def test_valid_auth_gives_result(self):
        result = self.get_headers_result('default', token=VALID_TOKEN_MAIN_TENANT)

        assert_that(result.status_code, equal_to(200))

    def test_invalid_auth_gives_401(self):
        result = self.get_headers_result('default', token='invalid-token')

        assert_that(result.status_code, equal_to(401))


class TestAuthenticationError(BaseDirdIntegrationTest):

    asset = 'no_auth_server'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stop_service(service_name='auth')

    def test_no_auth_server_gives_503(self):
        result = self.get_headers_result('default', token=VALID_TOKEN_MAIN_TENANT)

        assert_that(result.status_code, equal_to(503))
        assert_that(
            result.json()['reason'][0],
            contains_string('Authentication server unreachable'),
        )


class TestAuthenticationCoverage(BaseDirdIntegrationTest):

    asset = 'all_routes'

    def test_auth_on_headers(self):
        result_1 = self.get_headers_result('default')
        result_2 = self.get_headers_result('default', VALID_TOKEN_NO_ACL)

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))

    def test_auth_on_lookup(self):
        result_1 = self.get_lookup_result('something', 'default')
        result_2 = self.get_lookup_result('something', 'default', VALID_TOKEN_NO_ACL)

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))

    def test_auth_on_lookup_user(self):
        result_1 = self.get_lookup_user_result('something', 'default', VALID_UUID)
        result_2 = self.get_lookup_user_result(
            'something', 'default', VALID_UUID, VALID_TOKEN_NO_ACL
        )

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))

    def test_auth_on_reverse(self):
        result_1 = self.get_reverse_result('exten', 'default', 'uuid')
        result_2 = self.get_reverse_result(
            'exten', 'default', 'uuid', VALID_TOKEN_NO_ACL
        )

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))

    def test_auth_on_favorites_list(self):
        result_1 = self.get_favorites_result('default')
        result_2 = self.get_favorites_result('default', VALID_TOKEN_NO_ACL)

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))

    def test_auth_on_favorite_create(self):
        result_1 = self.put_favorite_result('source', 'contact')
        result_2 = self.put_favorite_result('source', 'contact', VALID_TOKEN_NO_ACL)

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))

    def test_auth_on_favorite_delete(self):
        result_1 = self.delete_favorite_result('source', 'contact')
        result_2 = self.delete_favorite_result('source', 'contact', VALID_TOKEN_NO_ACL)

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))

    def test_auth_on_personal_create(self):
        result_1 = self.post_personal_result({})
        result_2 = self.post_personal_result({}, VALID_TOKEN_NO_ACL)

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))

    def test_auth_on_personal_import(self):
        result_1 = self.import_personal_result('')
        result_2 = self.import_personal_result('', VALID_TOKEN_NO_ACL)

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))

    def test_auth_on_personal_list(self):
        result_1 = self.list_personal_result()
        result_2 = self.list_personal_result(VALID_TOKEN_NO_ACL)

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))

    def test_auth_on_personal_get(self):
        result_1 = self.get_personal_result('contact_id')
        result_2 = self.get_personal_result('contact_id', VALID_TOKEN_NO_ACL)

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))

    def test_auth_on_personal_edit(self):
        result_1 = self.put_personal_result('contact_id', {})
        result_2 = self.put_personal_result('contact_id', {}, VALID_TOKEN_NO_ACL)

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))

    def test_auth_on_personal_delete(self):
        result_1 = self.delete_personal_result('contact_id')
        result_2 = self.delete_personal_result('contact_id', VALID_TOKEN_NO_ACL)

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))

    def test_auth_on_personal_purge(self):
        result_1 = self.purge_personal_result()
        result_2 = self.purge_personal_result(VALID_TOKEN_NO_ACL)

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))

    def test_auth_on_personal_list_with_profile(self):
        result_1 = self.get_personal_with_profile_result('default')
        result_2 = self.get_personal_with_profile_result('default', VALID_TOKEN_NO_ACL)

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))
