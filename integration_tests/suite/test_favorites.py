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
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import equal_to
from hamcrest import has_entry


class TestAddRemoveFavorites(BaseDirdIntegrationTest):

    asset = 'csv_with_multiple_displays'

    def test_that_removed_favorites_are_not_listed(self):
        self.put_favorite('my_csv', '1')
        self.put_favorite('my_csv', '2')
        self.put_favorite('my_csv', '3')
        self.delete_favorite('my_csv', '2')

        result = self.favorites('default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555')),
            has_entry('column_values', contains('Charles', 'CCC', '555123555'))))


class TestFavoritesVisibility(BaseDirdIntegrationTest):

    asset = 'csv_with_multiple_displays'

    def test_that_favorites_are_only_visible_for_the_same_token(self):
        self.put_favorite('my_csv', '1', token='valid-token-1')
        self.put_favorite('my_csv', '2', token='valid-token-1')
        self.put_favorite('my_csv', '3', token='valid-token-2')

        result = self.favorites('default', token='valid-token-1')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555')),
            has_entry('column_values', contains('Bob', 'BBB', '5555551234'))))


class TestFavoritesPersistence(BaseDirdIntegrationTest):

    asset = 'csv_with_multiple_displays'

    def test_that_favorites_are_only_visible_for_the_same_token(self):
        self.put_favorite('my_csv', '1')

        result = self.favorites('default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555'))))

        self._run_cmd('docker-compose kill dird')
        self._run_cmd('docker-compose rm -f dird')
        self._run_cmd('docker-compose run --rm sync')

        result = self.favorites('default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555'))))


class TestRemovingFavoriteAlreadyInexistant(BaseDirdIntegrationTest):
    asset = 'sample_backend'

    def test_that_removing_an_inexisting_favorite_returns_404(self):
        result = self.delete_favorite_result('unknown_source', 'unknown_contact', token='valid-token')

        assert_that(result.status_code, equal_to(404))
