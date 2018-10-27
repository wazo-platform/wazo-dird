# -*- coding: utf-8 -*-
# Copyright 2015-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import (
    assert_that,
    contains,
    contains_inanyorder,
    equal_to,
    has_entry,
)
from xivo_test_helpers.bus import BusClient
from xivo_test_helpers import until

from .base_dird_integration_test import (
    BaseDirdIntegrationTest,
    VALID_TOKEN,
    VALID_TOKEN_1,
    VALID_TOKEN_2,
)


class TestFavorites(BaseDirdIntegrationTest):

    asset = 'csv_with_multiple_displays'

    def test_that_removed_favorites_are_not_listed(self):
        with self.favorite('my_csv', '1'), \
                self.favorite('my_csv', '2'), \
                self.favorite('my_csv', '3'):
            self.delete_favorite('my_csv', '2')
            result = self.favorites('default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555', True)),
            has_entry('column_values', contains('Charles', 'CCC', '555123555', True))))

    def test_that_favorites_are_only_visible_for_the_same_token(self):
        with self.favorite('my_csv', '1', token=VALID_TOKEN_1), \
                self.favorite('my_csv', '2', token=VALID_TOKEN_1), \
                self.favorite('my_csv', '3', token=VALID_TOKEN_2):
            result = self.favorites('default', token=VALID_TOKEN_1)

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555', True)),
            has_entry('column_values', contains('Bob', 'BBB', '5555551234', True))))

    def test_that_favorites_are_saved_across_dird_restart(self):
        with self.favorite('my_csv', '1'):
            result = self.favorites('default')

            assert_that(result['results'], contains_inanyorder(
                has_entry('column_values', contains('Alice', 'AAA', '5555555555', True))))

            self._run_cmd('docker-compose kill dird')
            self._run_cmd('docker-compose rm -f dird')
            self._run_cmd('docker-compose run --rm sync')

            result = self.favorites('default')

            assert_that(result['results'], contains_inanyorder(
                has_entry('column_values', contains('Alice', 'AAA', '5555555555', True))))

    def test_that_favorites_lookup_results_show_favorites(self):
        result = self.lookup('Ali', 'default', token=VALID_TOKEN_1)

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555', False))))

        with self.favorite('my_csv', '1', token=VALID_TOKEN_1):
            result = self.lookup('Ali', 'default', token=VALID_TOKEN_1)

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


class TestFavoritesInPersonalResults(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_personal_list_results_show_favorites(self):
        with self.personal({'firstname': 'Alice'}), \
                self.personal({'firstname': 'Bob'}) as bob, \
                self.personal({'firstname': 'Charlie'}):
            result = self.get_personal_with_profile('default')

            assert_that(result['results'], contains_inanyorder(
                has_entry('column_values', contains('Alice', None, None, False)),
                has_entry('column_values', contains('Bob', None, None, False)),
                has_entry('column_values', contains('Charlie', None, None, False))))

            with self.favorite('personal', bob['id']):
                personal = self.get_personal_with_profile('default')

        assert_that(personal['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', None, None, False)),
            has_entry('column_values', contains('Bob', None, None, True)),
            has_entry('column_values', contains('Charlie', None, None, False))))

    def test_that_favorites_list_results_accept_personal(self):
        with self.personal({'firstname': 'Alice'}) as alice:
            with self.favorite('personal', alice['id']):
                favorites = self.favorites('default')

        assert_that(favorites['results'], contains(
            has_entry('column_values', contains('Alice', None, None, True))))

    def test_that_removed_favorited_personal_are_not_listed_anymore(self):
        with self.personal({'firstname': 'Alice'}) as alice:
            self.put_favorite('personal', alice['id'])

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


class TestFavoritesBusEvents(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_adding_favorite_produces_bus_event(self):
        bus_port = self.service_port(5672, 'rabbitmq')
        bus = BusClient.from_connection_fields(host='localhost', port=bus_port)
        until.true(bus.is_up, tries=5)
        bus_events = bus.accumulator('directory.*.favorite.*')

        def favorite_bus_event_received(name):
            return name in (message['name'] for message in bus_events.accumulate())

        with self.personal({'firstname': 'Alice'}) as alice:
            with self.favorite('personal', alice['id']):
                until.true(favorite_bus_event_received, 'favorite_added', tries=2)

        until.true(favorite_bus_event_received, 'favorite_deleted', tries=2)
