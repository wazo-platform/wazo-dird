# -*- coding: utf-8 -*-

# Copyright (C) 2014 Avencall
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
from hamcrest import contains


class TestCSVBackend(BaseDirdIntegrationTest):

    asset = 'csv_with_multiple_displays'

    def test_that_searching_for_lice_return_Alice(self):
        result = self.lookup('lice', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains('Alice', 'AAA', '5555555555'))


class TestCSVNoUnique(BaseDirdIntegrationTest):

    asset = 'csv_with_no_unique_columns'

    def test_lookup_should_work_without_unique_columns(self):
        result = self.lookup('lice', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains('Alice', 'AAA', '5555555555'))
