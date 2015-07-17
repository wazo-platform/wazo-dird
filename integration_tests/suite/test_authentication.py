# -*- coding: utf-8 -*-

# Copyright (C) 2015 Avencall
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

from hamcrest import assert_that
from hamcrest import contains_string
from hamcrest import equal_to


class TestAuthentication(BaseDirdIntegrationTest):

    asset = 'auth-only'

    def test_no_auth_gives_401(self):
        result = self.get_headers_result('default', token=None)

        assert_that(result.status_code, equal_to(401))

    def test_valid_auth_gives_result(self):
        result = self.get_headers_result('default', token='valid-token')

        assert_that(result.status_code, equal_to(200))

    def test_invalid_auth_gives_401(self):
        result = self.get_headers_result('default', token='invalid-token')

        assert_that(result.status_code, equal_to(401))


class TestAuthenticationErrro(BaseDirdIntegrationTest):

    asset = 'no_auth_server'

    def test_no_auth_server_gives_503(self):
        result = self.get_headers_result('default', token='valid-token')

        assert_that(result.status_code, equal_to(503))
        assert_that(result.json()['reason'][0], contains_string('inexisting-auth-server:9497'))


class TestAuthenticationCoverage(BaseDirdIntegrationTest):

    asset = 'all_routes'

    def test_auth_on_headers(self):
        result = self.get_headers_result('default')

        assert_that(result.status_code, equal_to(401))

    def test_auth_on_lookup(self):
        result = self.get_lookup_result('something', 'default')

        assert_that(result.status_code, equal_to(401))

    def test_auth_on_favorites_list(self):
        result = self.get_favorites_result('default')

        assert_that(result.status_code, equal_to(401))

    def test_auth_on_favorite_create(self):
        result = self.put_favorite_result('source', 'contact')

        assert_that(result.status_code, equal_to(401))

    def test_auth_on_favorite_delete(self):
        result = self.delete_favorite_result('source', 'contact')

        assert_that(result.status_code, equal_to(401))

    def test_auth_on_private_create(self):
        result = self.post_private_result({})

        assert_that(result.status_code, equal_to(401))

    def test_auth_on_private_list(self):
        result = self.get_privates_result()

        assert_that(result.status_code, equal_to(401))

    def test_auth_on_private_delete(self):
        result = self.delete_private_result('contact_id')

        assert_that(result.status_code, equal_to(401))
