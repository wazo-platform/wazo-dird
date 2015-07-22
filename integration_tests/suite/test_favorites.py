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
            has_entry('column_values', contains('Alice', 'AAA', '5555555555', True)),
            has_entry('column_values', contains('Charles', 'CCC', '555123555', True))))


class TestFavoritesVisibility(BaseDirdIntegrationTest):

    asset = 'csv_with_multiple_displays'

    def test_that_favorites_are_only_visible_for_the_same_token(self):
        self.put_favorite('my_csv', '1', token='valid-token-1')
        self.put_favorite('my_csv', '2', token='valid-token-1')
        self.put_favorite('my_csv', '3', token='valid-token-2')

        result = self.favorites('default', token='valid-token-1')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555', True)),
            has_entry('column_values', contains('Bob', 'BBB', '5555551234', True))))


class TestFavoritesPersistence(BaseDirdIntegrationTest):

    asset = 'csv_with_multiple_displays'

    def test_that_privates_are_saved_across_dird_restart(self):
        self.put_favorite('my_csv', '1')

        result = self.favorites('default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555', True))))

        self._run_cmd('docker-compose kill dird')
        self._run_cmd('docker-compose rm -f dird')
        self._run_cmd('docker-compose run --rm sync')

        result = self.favorites('default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555', True))))


class TestRemovingFavoriteAlreadyInexistant(BaseDirdIntegrationTest):
    asset = 'sample_backend'

    def test_that_removing_an_inexisting_favorite_returns_404(self):
        result = self.delete_favorite_result('unknown_source', 'unknown_contact', token='valid-token')

        assert_that(result.status_code, equal_to(404))


class TestFavoritesInLookupResults(BaseDirdIntegrationTest):

    asset = 'csv_with_multiple_displays'

    def test_that_favorites_lookup_results_show_favorites(self):
        result = self.lookup('Ali', 'default', token='valid-token-1')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555', False))))

        self.put_favorite('my_csv', '1', token='valid-token-1')

        result = self.lookup('Ali', 'default', token='valid-token-1')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555', True))))


class TestFavoritesInPrivatesResults(BaseDirdIntegrationTest):

    asset = 'privates_only'

    def test_that_privates_list_results_show_favorites(self):
        self.post_private({'firstname': 'Alice'})
        bob = self.post_private({'firstname': 'Bob'})
        self.post_private({'firstname': 'Charlie'})

        result = self.get_privates_with_profile('default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', None, None, False)),
            has_entry('column_values', contains('Bob', None, None, False)),
            has_entry('column_values', contains('Charlie', None, None, False))))

        self.put_favorite('privates', bob['id'])

        privates = self.get_privates_with_profile('default')

        assert_that(privates['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', None, None, False)),
            has_entry('column_values', contains('Bob', None, None, True)),
            has_entry('column_values', contains('Charlie', None, None, False))))


class TestPrivatesInFavoritesList(BaseDirdIntegrationTest):

    asset = 'privates_only'

    def test_that_favorites_list_results_accept_privates(self):
        alice = self.post_private({'firstname': 'Alice'})
        self.put_favorite('privates', alice['id'])

        favorites = self.favorites('default')

        assert_that(favorites['results'], contains(
            has_entry('column_values', contains('Alice', None, None, True))))


class TestDeleteFavoritePrivate(BaseDirdIntegrationTest):

    asset = 'privates_only'

    def test_that_removed_favorited_privates_are_not_listed_anymore(self):
        alice = self.post_private({'firstname': 'Alice'})
        self.put_favorite('privates', alice['id'])
        self.delete_private(alice['id'])

        favorites = self.favorites('default')

        assert_that(favorites['results'], contains())


class TestFavoritesVisibilityInSimilarSources(BaseDirdIntegrationTest):

    asset = 'similar_sources'

    def test_that_favorites_are_only_visible_for_the_exact_source(self):
        self.put_favorite('csv_2', '1', token='valid-token-1')

        result = self.favorites('default', token='valid-token-1')

        # No values from source 'csv', id '1'
        assert_that(result['results'], contains(
            has_entry('column_values', contains('Alice', 'Alan', '1111', True))))
