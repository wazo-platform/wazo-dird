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
from hamcrest import contains_inanyorder


class TestCoreSourceManagement(BaseDirdIntegrationTest):

    asset = 'multiple_sources'

    def test_multiple_source_from_the_same_backend(self):
        result = self.lookup('lice', 'default')

        # second_csv does not search in column firstname
        expected_results = [
            {'column_values': ['Alice', 'AAA', '5555555555'],
             'source': 'my_csv',
             'relations': {'user': None, 'endpoint': None, 'agent': None}},
            {'column_values': ['Alice', 'Alan', '1111'],
             'source': 'third_csv',
             'relations': {'user': None, 'endpoint': None, 'agent': None}},
        ]

        assert_that(result['results'],
                    contains_inanyorder(*expected_results))


class TestCoreSourceLoadingWithABrokenConfig(BaseDirdIntegrationTest):

    asset = 'broken_source_config'

    def test_multiple_source_from_the_same_backend(self):
        result = self.lookup('lice', 'default')

        expected_results = [
            {'column_values': ['Alice', 'AAA', '5555555555'],
             'source': 'my_csv',
             'relations': {'user': None, 'endpoint': None, 'agent': None}},
        ]

        assert_that(result['results'],
                    contains_inanyorder(*expected_results))


class TestDisplay(BaseDirdIntegrationTest):

    asset = 'csv_with_multiple_displays'

    def test_that_the_display_is_really_applied_to_lookup(self):
        result = self.lookup('lice', 'default')

        assert_that(result['column_headers'], contains('Firstname', 'Lastname', 'Number'))
        assert_that(result['column_types'], contains(None, None, None))

    def test_display_with_a_type_only(self):
        result = self.lookup('lice', 'test')

        assert_that(result['column_headers'], contains('fn', 'ln', 'Empty', None, 'Default'))
        assert_that(result['column_types'], contains('firstname', None, None, 'status', None))
        assert_that(result['results'][0]['column_values'],
                    contains('Alice', 'AAA', None, None, 'Default'))

    def test_that_the_display_is_applied_to_headers(self):
        result = self.headers('default')

        assert_that(result['column_headers'], contains('Firstname', 'Lastname', 'Number'))
        assert_that(result['column_types'], contains(None, None, None))

    def test_display_on_headers_with_no_title(self):
        result = self.headers('test')

        assert_that(result['column_headers'],
                    contains('fn', 'ln', 'Empty', None, 'Default'))
        assert_that(result['column_types'],
                    contains('firstname', None, None, 'status', None))
