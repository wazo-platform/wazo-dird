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
from hamcrest import contains_inanyorder
from hamcrest import equal_to
from hamcrest import matches_regexp


class TestPersonalExport(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def tearDown(self):
        self.clear_personal()

    def test_that_export_empty_returns_204(self):
        result = self.export_personal_result('valid-token')
        assert_that(result.status_code, equal_to(204))

    def test_that_export_full_returns_all_contacts(self):
        self.post_personal({'firstname': 'Alice', 'lastname': 'Aldertion'})
        self.post_personal({'firstname': 'Bob', 'lastname': 'Bodkartan'})

        result = self.export_personal()

        result = result.split('\r\n')
        assert_that(result[0], equal_to('firstname,id,lastname'))
        assert_that(result[1:-1], contains_inanyorder(matches_regexp('Alice,[^,]*,Aldertion'),
                                                      matches_regexp('Bob,[^,]*,Bodkartan')))
        assert_that(result[-1], equal_to(''))

    def test_that_export_full_mixes_all_headers(self):
        self.post_personal({'firstname': 'Alice'})
        self.post_personal({'lastname': 'Bodkartan'})

        result = self.export_personal()

        result = result.split('\r\n')
        assert_that(result[0], equal_to('firstname,id,lastname'))
        assert_that(result[1:-1], contains_inanyorder(matches_regexp('Alice,[^,]*,'),
                                                      matches_regexp(',[^,]*,Bodkartan')))
        assert_that(result[-1], equal_to(''))

    def test_that_export_with_non_ascii_is_ok(self):
        self.post_personal({'firstname': u'Éloïse'})

        result = self.export_personal()

        result = result.split('\r\n')
        assert_that(result[0], equal_to('firstname,id'))
        assert_that(result[1:-1], contains_inanyorder(matches_regexp(u'Éloïse,[^,]*')))
        assert_that(result[-1], equal_to(''))
