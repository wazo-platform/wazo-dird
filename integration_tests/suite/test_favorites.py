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

import requests

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import equal_to
from hamcrest import has_entry
from xivo_test_helpers import until

from .base_dird_integration_test import BaseDirdIntegrationTest
from .base_dird_integration_test import VALID_TOKEN
from .base_dird_integration_test import VALID_TOKEN_1
from .base_dird_integration_test import VALID_TOKEN_2


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
        self.put_favorite('my_csv', '1', token=VALID_TOKEN_1)
        self.put_favorite('my_csv', '2', token=VALID_TOKEN_1)
        self.put_favorite('my_csv', '3', token=VALID_TOKEN_2)

        result = self.favorites('default', token=VALID_TOKEN_1)

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555', True)),
            has_entry('column_values', contains('Bob', 'BBB', '5555551234', True))))


class TestFavoritesPersistence(BaseDirdIntegrationTest):

    asset = 'csv_with_multiple_displays'

    def test_that_favorites_are_saved_across_dird_restart(self):
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
        result = self.delete_favorite_result('unknown_source', 'unknown_contact', token=VALID_TOKEN)

        assert_that(result.status_code, equal_to(404))


class TestFavoritesWithOneBrokenSource(BaseDirdIntegrationTest):

    asset = 'half_broken'

    def test_that_listing_favorites_of_a_broken_source_returns_favorites_from_other_sources(self):
        self.put_favorite('my_csv', '1')
        self.put_favorite('broken', '1')

        result = self.favorites('default')

        assert_that(result['results'], contains(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555'))))


class TestFavoritesInLookupResults(BaseDirdIntegrationTest):

    asset = 'csv_with_multiple_displays'

    def test_that_favorites_lookup_results_show_favorites(self):
        result = self.lookup('Ali', 'default', token=VALID_TOKEN_1)

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555', False))))

        self.put_favorite('my_csv', '1', token=VALID_TOKEN_1)

        result = self.lookup('Ali', 'default', token=VALID_TOKEN_1)

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555', True))))


class TestFavoritesInPersonalResults(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_personal_list_results_show_favorites(self):
        self.post_personal({'firstname': 'Alice'})
        bob = self.post_personal({'firstname': 'Bob'})
        self.post_personal({'firstname': 'Charlie'})

        result = self.get_personal_with_profile('default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', None, None, False)),
            has_entry('column_values', contains('Bob', None, None, False)),
            has_entry('column_values', contains('Charlie', None, None, False))))

        self.put_favorite('personal', bob['id'])

        personal = self.get_personal_with_profile('default')

        assert_that(personal['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', None, None, False)),
            has_entry('column_values', contains('Bob', None, None, True)),
            has_entry('column_values', contains('Charlie', None, None, False))))


class TestPersonalInFavoritesList(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_favorites_list_results_accept_personal(self):
        alice = self.post_personal({'firstname': 'Alice'})
        self.put_favorite('personal', alice['id'])

        favorites = self.favorites('default')

        assert_that(favorites['results'], contains(
            has_entry('column_values', contains('Alice', None, None, True))))


class TestDeleteFavoritePersonal(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_removed_favorited_personal_are_not_listed_anymore(self):
        alice = self.post_personal({'firstname': 'Alice'})
        self.put_favorite('personal', alice['id'])
        self.delete_personal(alice['id'])

        favorites = self.favorites('default')

        assert_that(favorites['results'], contains())


class TestFavoritesVisibilityInSimilarSources(BaseDirdIntegrationTest):

    asset = 'similar_sources'

    def test_that_favorites_are_only_visible_for_the_exact_source(self):
        self.put_favorite('csv_2', '1', token=VALID_TOKEN_1)

        result = self.favorites('default', token=VALID_TOKEN_1)

        # No values from source 'csv', id '1'
        assert_that(result['results'], contains(
            has_entry('column_values', contains('Alice', 'Alan', '1111', True))))


class TestConsulUnreachable(BaseDirdIntegrationTest):

    asset = 'no_consul'

    def test_when_consul_errors_that_favorites_actions_return_503(self):
        result = self.get_favorites_result('default', 'valid-token')
        assert_that(result.status_code, equal_to(503))
        result = self.put_favorite_result('some-source', 'some-id', 'valid-token')
        assert_that(result.status_code, equal_to(503))
        result = self.delete_favorite_result('some-source', 'some-id', 'valid-token')
        assert_that(result.status_code, equal_to(503))
