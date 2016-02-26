# -*- coding: utf-8 -*-

# Copyright (C) 2015-2016 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

from .base_dird_integration_test import BaseDirdIntegrationTest
from .base_dird_integration_test import VALID_TOKEN
from .base_dird_integration_test import VALID_TOKEN_NO_ACL

from hamcrest import assert_that
from hamcrest import contains_string
from hamcrest import equal_to


class TestAuthentication(BaseDirdIntegrationTest):

    asset = 'auth-only'

    def test_no_auth_gives_401(self):
        result = self.get_headers_result('default', token=None)

        assert_that(result.status_code, equal_to(401))

    def test_valid_auth_gives_result(self):
        result = self.get_headers_result('default', token=VALID_TOKEN)

        assert_that(result.status_code, equal_to(200))

    def test_invalid_auth_gives_401(self):
        result = self.get_headers_result('default', token='invalid-token')

        assert_that(result.status_code, equal_to(401))


class TestAuthenticationError(BaseDirdIntegrationTest):

    asset = 'no_auth_server'

    def test_no_auth_server_gives_503(self):
        result = self.get_headers_result('default', token=VALID_TOKEN)

        assert_that(result.status_code, equal_to(503))
        assert_that(result.json()['reason'][0], contains_string('Authentication server unreachable'))


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

    def test_auth_on_reverse(self):
        result_1 = self.get_reverse_result('exten', 'default', 'uuid')
        result_2 = self.get_reverse_result('exten', 'default', 'uuid', VALID_TOKEN_NO_ACL)

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

    def test_auth_on_menu_cisco(self):
        result_1 = self.get_menu_cisco_result('default', 'uuid')
        result_2 = self.get_menu_cisco_result('default', 'uuid', token=VALID_TOKEN_NO_ACL)

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))

    def test_auth_on_input_cisco(self):
        result_1 = self.get_input_cisco_result('default', 'uuid')
        result_2 = self.get_input_cisco_result('default', 'uuid', token=VALID_TOKEN_NO_ACL)

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))

    def test_auth_on_lookup_cisco(self):
        result_1 = self.get_lookup_cisco_result('default', 'uuid')
        result_2 = self.get_lookup_cisco_result('default', 'uuid', token=VALID_TOKEN_NO_ACL)

        assert_that(result_1.status_code, equal_to(401))
        assert_that(result_2.status_code, equal_to(401))
