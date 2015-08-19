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

from hamcrest import (assert_that, contains, contains_inanyorder,
                      has_entry, has_length)


class TestCSVWSBackend(BaseDirdIntegrationTest):

    asset = 'csv_ws_utf8_with_pipes'

    def test_that_searching_for_result_with_non_ascii(self):
        results = self.lookup(u'dré', 'default')

        assert_that(results['results'][0],
                    has_entry('column_values', contains(u'Andrée-Anne', 'Smith', '5551231111', False)))
        assert_that(results['results'], has_length(1))

    def test_that_no_result_returns_an_empty_list(self):
        results = self.lookup('henry', 'default')

        assert_that(results['results'], has_length(0))

    def test_that_results_can_be_favorited(self):
        self.put_favorite('my_csv', '42')

        result = self.favorites('default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains(u'Benoît', 'Malone', '5551232222', True),)
        ))


class TestCSVWSBackend2(BaseDirdIntegrationTest):

    asset = 'csv_ws_iso88591_with_coma'

    def test_that_searching_for_result_with_non_ascii(self):
        results = self.lookup(u'dré', 'default')

        assert_that(results['results'][0],
                    has_entry('column_values', contains(u'Andrée-Anne', 'Smith', '5551231111', False)))

    def test_that_no_result_returns_an_empty_list(self):
        results = self.lookup('henry', 'default')

        assert_that(results['results'], has_length(0))

    def test_that_results_can_be_favorited(self):
        self.put_favorite('my_csv', '42')

        result = self.favorites('default')

        first_result = result['results'][0]['column_values']
        assert_that(first_result, contains(u'Benoît', 'Malone', '5551232222', True))
