# Copyright 2015-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import uuid
from hamcrest import assert_that, contains, contains_inanyorder, equal_to, has_entry
from wazo_test_helpers.bus import BusClient
from wazo_test_helpers import until
from wazo_test_helpers.auth import AuthClient as MockAuthClient, MockUserToken

from .helpers.base import (
    BaseDirdIntegrationTest,
    CSVWithMultipleDisplayTestCase,
    PersonalOnlyTestCase,
)
from .helpers.config import new_csv_with_multiple_displays_config
from .helpers.constants import MAIN_TENANT, TENANT_UUID_2, VALID_TOKEN_MAIN_TENANT


class _BaseMultiTokenFavoriteTest(BaseDirdIntegrationTest):

    asset = 'all_routes'
    config_factory = new_csv_with_multiple_displays_config

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tenants = {
            'items': [
                {'uuid': MAIN_TENANT, 'name': 'first'},
                {'uuid': TENANT_UUID_2, 'name': 'second'},
            ]
        }
        mock_auth_client = MockAuthClient('127.0.0.1', cls.service_port(9497, 'auth'))
        user_token_1 = MockUserToken.some_token(
            metadata={'tenant_uuid': tenants['items'][0]['uuid']}
        )
        user_token_2 = MockUserToken.some_token(
            metadata={'tenant_uuid': tenants['items'][1]['uuid']}
        )
        user_token_3 = MockUserToken.some_token(
            metadata={'tenant_uuid': tenants['items'][0]['uuid']}
        )
        mock_auth_client.set_token(user_token_1)
        mock_auth_client.set_token(user_token_2)
        mock_auth_client.set_token(user_token_3)
        mock_auth_client.set_tenants(tenants)
        cls.token_1 = user_token_1.token_id
        cls.token_2 = user_token_2.token_id
        cls.token_3 = user_token_3.token_id


class TestFavorites(_BaseMultiTokenFavoriteTest):
    def test_that_removed_favorites_are_not_listed(self):
        with self.favorite('my_csv', '1', token=self.token_1), self.favorite(
            'my_csv', '2', token=self.token_1
        ), self.favorite('my_csv', '3', token=self.token_1):
            self.delete_favorite('my_csv', '2', token=self.token_1)
            result = self.favorites('default', token=self.token_1)

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entry(
                    'column_values', contains('Alice', 'AAA', '5555555555', True)
                ),
                has_entry(
                    'column_values', contains('Charles', 'CCC', '555123555', True)
                ),
            ),
        )

    def test_that_favorites_are_only_visible_for_the_same_token(self):
        with self.favorite('my_csv', '1', token=self.token_1), self.favorite(
            'my_csv', '2', token=self.token_1
        ), self.favorite('my_csv', '3', token=self.token_3):
            result = self.favorites('default', token=self.token_1)

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entry(
                    'column_values', contains('Alice', 'AAA', '5555555555', True)
                ),
                has_entry('column_values', contains('Bob', 'BBB', '5555551234', True)),
            ),
        )

    def test_that_favorites_are_saved_across_dird_restart(self):
        with self.favorite('my_csv', '1', token=self.token_1):
            result = self.favorites('default', token=self.token_1)

            assert_that(
                result['results'],
                contains_inanyorder(
                    has_entry(
                        'column_values', contains('Alice', 'AAA', '5555555555', True)
                    )
                ),
            )

            self._run_cmd('docker-compose kill dird')
            self._run_cmd('docker-compose rm -f dird')
            self._run_cmd('docker-compose run --rm sync')

            result = self.favorites('default', token=self.token_1)

            assert_that(
                result['results'],
                contains_inanyorder(
                    has_entry(
                        'column_values', contains('Alice', 'AAA', '5555555555', True)
                    )
                ),
            )

    def test_that_favorites_lookup_results_show_favorites(self):
        result = self.lookup('Ali', 'default', token=self.token_1)

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entry(
                    'column_values', contains('Alice', 'AAA', '5555555555', False)
                )
            ),
        )

        with self.favorite('my_csv', '1', token=self.token_1):
            result = self.lookup('Ali', 'default', token=self.token_1)

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entry('column_values', contains('Alice', 'AAA', '5555555555', True))
            ),
        )


class TestRemovingFavoriteAlreadyInexistant(CSVWithMultipleDisplayTestCase):
    def test_that_removing_an_inexisting_favorite_returns_404(self):
        result = self.delete_favorite_result(
            'unknown_source', 'unknown_contact', token=VALID_TOKEN_MAIN_TENANT
        )

        assert_that(result.status_code, equal_to(404))


class TestFavoritesInPersonalResults(PersonalOnlyTestCase):
    def test_that_personal_list_results_show_favorites(self):
        with self.personal({'firstname': 'Alice'}), self.personal(
            {'firstname': 'Bob'}
        ) as bob, self.personal({'firstname': 'Charlie'}):
            result = self.get_personal_with_profile('default')

            assert_that(
                result['results'],
                contains_inanyorder(
                    has_entry('column_values', contains('Alice', None, None, False)),
                    has_entry('column_values', contains('Bob', None, None, False)),
                    has_entry('column_values', contains('Charlie', None, None, False)),
                ),
            )

            with self.favorite('personal', bob['id']):
                personal = self.get_personal_with_profile('default')

        assert_that(
            personal['results'],
            contains_inanyorder(
                has_entry('column_values', contains('Alice', None, None, False)),
                has_entry('column_values', contains('Bob', None, None, True)),
                has_entry('column_values', contains('Charlie', None, None, False)),
            ),
        )

    def test_that_favorites_list_results_accept_personal(self):
        with self.personal({'firstname': 'Alice'}) as alice:
            with self.favorite('personal', alice['id']):
                favorites = self.favorites('default')

        assert_that(
            favorites['results'],
            contains(has_entry('column_values', contains('Alice', None, None, True))),
        )

    def test_that_removed_favorited_personal_are_not_listed_anymore(self):
        with self.personal({'firstname': 'Alice'}) as alice:
            self.put_favorite('personal', alice['id'])

        favorites = self.favorites('default')

        assert_that(favorites['results'], contains())


class TestFavoritesBusEvents(PersonalOnlyTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tenants = {
            'items': [
                {'uuid': str(uuid.uuid4()), 'name': 'first'},
                {'uuid': str(uuid.uuid4()), 'name': 'second'},
            ]
        }
        mock_auth_client = MockAuthClient('127.0.0.1', cls.service_port(9497, 'auth'))
        user_token_1 = MockUserToken.some_token(
            metadata={'tenant_uuid': tenants['items'][0]['uuid']}
        )
        user_token_2 = MockUserToken.some_token(
            metadata={'tenant_uuid': tenants['items'][1]['uuid']}
        )
        mock_auth_client.set_token(user_token_1)
        mock_auth_client.set_token(user_token_2)
        mock_auth_client.set_tenants(tenants)
        cls.token_1 = user_token_1.token_id
        cls.token_2 = user_token_2.token_id

    def test_that_adding_favorite_produces_bus_event(self):
        bus_port = self.service_port(5672, 'rabbitmq')
        bus = BusClient.from_connection_fields(host='127.0.0.1', port=bus_port)
        until.true(bus.is_up, tries=5)
        bus_events = bus.accumulator('directory.*.favorite.*')

        def favorite_bus_event_received(name):
            return name in (message['name'] for message in bus_events.accumulate())

        with self.personal({'firstname': 'Alice'}) as alice:
            with self.favorite('personal', alice['id']):
                until.true(favorite_bus_event_received, 'favorite_added', tries=2)

        until.true(favorite_bus_event_received, 'favorite_deleted', tries=2)
