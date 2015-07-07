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

    def test_that_searching_for_ali_returns_alice(self):
        results = self.lookup('ali', 'default')

        assert_that(results['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'Smith', '5551231111', False))))

    def test_that_no_result_returns_an_empty_list(self):
        results = self.lookup('henry', 'default')

        assert_that(results['results'], has_length(0))

    def test_that_results_can_be_favorited(self):
        self.put_favorite('my_csv', '42')

        result = self.favorites('default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Bob', 'Malone', '5551232222', True),)
        ))
