# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unicodedata
import unittest
from typing import Any, cast
from unittest.mock import Mock, patch

from hamcrest import (
    assert_that,
    contains_exactly,
    empty,
    equal_to,
    has_entries,
    has_length,
)
from requests.exceptions import ConnectionError, HTTPError

from wazo_dird.exception import WazoConfdError
from wazo_dird.plugins.base_plugins import SourcePluginDependencies

from ..plugin import WazoUserPlugin
from ..schemas import contact_list_param_schema
from .test_user_snapshot import SOURCE_CONFIG, make_user


def _user(user_id: int, firstname: str, lastname: str | None) -> dict[str, Any]:
    user = make_user(user_id, firstname, lastname or '', str(1000 + user_id))
    user['lastname'] = lastname  # the directory view sends null, not ''
    return user


# ties on the first name, on the case, and on accents; user 4 has no lastname
USERS = [
    _user(1, 'Zoe', 'Zimmer'),
    _user(2, 'anna', 'Martin'),
    _user(3, 'Anna', 'Bernard'),
    _user(4, 'Émile', None),
    _user(5, 'Élodie', 'Dubois'),
    _user(6, 'Bob', 'Éclair'),
    _user(7, 'Bob', 'Abel'),
]


def listing(**query: str) -> dict[str, Any]:
    """The parameters dird gives to the listing for this query string."""
    return contact_list_param_schema.load(query)


class FakeConfd:
    """GET /users like confd: SQL order by lastname, then a Python collated sort."""

    def __init__(self) -> None:
        self.users = list(USERS)
        self.calls: list[dict[str, Any]] = []
        self.failure: Exception | None = None
        self.snapshot_failure: Exception | None = None

    def infos(self) -> dict[str, str]:
        return {'uuid': 'my-xivo-uuid'}

    def users_list(self, **params: Any) -> dict[str, Any]:
        self.calls.append(params)
        if self.failure is not None:
            raise self.failure
        if self.snapshot_failure is not None and params.get('order') == 'id':
            raise self.snapshot_failure

        rows = list(self.users)
        if params.get('search'):
            needle = params['search'].lower()
            rows = [u for u in rows if needle in f"{u['firstname']} {u['lastname']}"]
        if isinstance(params.get('uuid'), str):
            wanted = params['uuid'].split(',')
            rows = [u for u in rows if u['uuid'] in wanted]
        for column in ('firstname', 'lastname'):
            if params.get(column):
                rows = [u for u in rows if u[column] == params[column]]

        rows.sort(key=lambda user: (user['lastname'] or '').lower())
        order = params.get('order') or 'lastname'

        def key(user: dict[str, Any]) -> tuple[bool, str]:
            text = '' if user[order] is None else str(user[order])
            if order in ('firstname', 'lastname'):
                text = text.casefold()
            return (text == '', unicodedata.normalize('NFKD', text))

        rows.sort(key=key, reverse=params.get('direction') == 'desc')
        offset, limit = params.get('offset', 0), params.get('limit')
        page = rows[offset:] if not limit else rows[offset : offset + limit]
        return {'items': page, 'total': len(rows)}

    def snapshot_loads(self) -> list[dict[str, Any]]:
        return [call for call in self.calls if call.get('order') == 'id']

    def listings(self) -> list[dict[str, Any]]:
        return [call for call in self.calls if call.get('order') != 'id']


class TestListContacts(unittest.TestCase):
    def setUp(self) -> None:
        self.confd = FakeConfd()
        self.client = Mock(host='confd', port=9486, timeout=10)
        self.client.users.list.side_effect = self.confd.users_list
        self.client.infos.side_effect = self.confd.infos
        self.now = 1000.0
        patcher = patch(
            'wazo_dird.plugins.wazo_user_backend.plugin.monotonic', lambda: self.now
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_plugin(self, ttl: int = 60, **config: Any) -> WazoUserPlugin:
        dependencies = {
            'config': {**SOURCE_CONFIG, **config},
            'main_config': {'wazo_user_cache_ttl': ttl},
            'auth_client': Mock(),
            'token_renewer': Mock(),
        }
        plugin = WazoUserPlugin()
        with patch('wazo_dird.plugins.wazo_user_backend.plugin.registry') as registry:
            registry.get.return_value = self.client
            plugin.load(cast(SourcePluginDependencies, dependencies))
        return plugin

    def ids(self, plugin: WazoUserPlugin, **query: str) -> list[Any]:
        result = plugin.list_contacts(**listing(**query))
        return [user['id'] for user in result['items']]

    def test_listing_is_what_confd_lists(self) -> None:
        live, cached = self.make_plugin(ttl=0), self.make_plugin()
        queries: list[dict[str, str]] = [
            {},
            {'offset': '0', 'order': 'firstname'},
            {'order': 'lastname'},
            {'direction': 'desc'},
            {'order': 'lastname', 'direction': 'desc'},
            {'limit': '3'},
            {'limit': '3', 'offset': '2'},
            {'limit': '2', 'offset': '6', 'order': 'lastname', 'direction': 'desc'},
            {'offset': '5'},
            {'offset': '100'},
            {'limit': '100'},
        ]
        for query in queries:
            with self.subTest(query=query):
                assert_that(
                    cached.list_contacts(**listing(**query)),
                    equal_to(live.list_contacts(**listing(**query))),
                )

    def test_names_sort_without_case_nor_accents_and_empty_ones_last(self) -> None:
        plugin = self.make_plugin()

        assert_that(self.ids(plugin), contains_exactly(3, 2, 7, 6, 5, 4, 1))
        assert_that(
            self.ids(plugin, order='lastname'), contains_exactly(7, 3, 5, 6, 2, 1, 4)
        )
        assert_that(
            self.ids(plugin, direction='desc'), contains_exactly(1, 4, 5, 7, 6, 3, 2)
        )

    def test_total_counts_every_user_whatever_the_page(self) -> None:
        plugin = self.make_plugin()

        result = plugin.list_contacts(**listing(limit='2', offset='1'))

        assert_that(result['total'], equal_to(7))
        assert_that(result['items'], has_length(2))

    def test_items_have_the_fields_confd_sends(self) -> None:
        plugin = self.make_plugin()

        result = plugin.list_contacts(**listing(limit='1', order='lastname'))

        assert_that(result['items'], contains_exactly(USERS[6]))

    def test_the_snapshot_load_is_the_only_request_of_the_listings(self) -> None:
        plugin = self.make_plugin()

        plugin.list_contacts(**listing())
        plugin.list_contacts(**listing(order='lastname'))
        plugin.list_contacts(**listing(limit='2'))

        assert_that(self.confd.calls, has_length(1))
        assert_that(self.confd.snapshot_loads(), has_length(1))

    def test_the_listing_changes_after_the_ttl(self) -> None:
        plugin = self.make_plugin()
        assert_that(self.ids(plugin, limit='1'), contains_exactly(3))
        self.confd.users.append(_user(8, 'Aaron', 'Zed'))

        self.now += 59
        assert_that(self.ids(plugin, limit='1'), contains_exactly(3))
        self.now += 2
        assert_that(self.ids(plugin, limit='1'), contains_exactly(8))

    def test_what_the_snapshot_cannot_reproduce_asks_confd(self) -> None:
        plugin = self.make_plugin()
        uuid = USERS[0]['uuid']
        queries: list[dict[str, str]] = [
            {'search': 'anna'},
            {'uuid': uuid, 'search': 'anna'},
            {'uuid': uuid, 'recurse': 'true'},
            {'uuid': uuid, 'firstname': 'Zoe'},
            {'firstname': 'Bob'},
            {'lastname': 'Abel'},
            {'recurse': 'true'},
            {'limit': '0'},
        ]
        for query in queries:
            with self.subTest(query=query):
                self.confd.calls.clear()
                params = listing(**query)

                result = plugin.list_contacts(**params)

                assert_that(
                    self.confd.calls, contains_exactly({'view': 'directory', **params})
                )
                assert_that(result, equal_to(self.confd.users_list(**params)))

    def test_a_batch_of_uuids_lists_those_users_sorted_as_confd_sorts(self) -> None:
        plugin = self.make_plugin()
        batch = ','.join(USERS[i]['uuid'] for i in (0, 2, 4, 5))

        assert_that(self.ids(plugin, uuid=batch), contains_exactly(3, 6, 5, 1))
        assert_that(
            self.ids(plugin, uuid=batch, direction='desc'), contains_exactly(1, 5, 6, 3)
        )

    def test_unknown_uuids_match_nothing_and_a_repeated_one_gives_one_user(
        self,
    ) -> None:
        plugin = self.make_plugin()
        known = USERS[0]['uuid']
        unknown = '00000000-0000-0000-0000-00000000ffff'
        # confd matches the text exactly: no trimming
        batches = [f'{unknown},{known},{known},{unknown}', f'{known} ,{unknown}']

        assert_that(self.ids(plugin, uuid=batches[0]), contains_exactly(1))
        assert_that(self.ids(plugin, uuid=batches[1]), empty())

    def test_an_empty_uuid_matches_nothing_as_in_confd(self) -> None:
        live, cached = self.make_plugin(ttl=0), self.make_plugin()

        result = cached.list_contacts(**listing(uuid=''))

        assert_that(result, equal_to({'total': 0, 'items': []}))
        assert_that(result, equal_to(live.list_contacts(**listing(uuid=''))))

    def test_the_page_and_the_total_follow_the_uuid_filter(self) -> None:
        plugin = self.make_plugin()
        batch = ','.join(user['uuid'] for user in USERS[:5])

        result = plugin.list_contacts(
            **listing(uuid=batch, limit='2', offset='1', order='lastname')
        )

        assert_that(result['total'], equal_to(5))
        assert_that([user['id'] for user in result['items']], contains_exactly(5, 2))

    def test_a_uuid_listing_is_what_confd_lists(self) -> None:
        live, cached = self.make_plugin(ttl=0), self.make_plugin()
        everyone = ','.join(user['uuid'] for user in USERS)
        some = ','.join(USERS[i]['uuid'] for i in (6, 1, 3))
        queries: list[dict[str, str]] = [
            {'uuid': everyone},
            {'uuid': some},
            {'uuid': some, 'order': 'lastname'},
            {'uuid': some, 'direction': 'desc'},
            {'uuid': everyone, 'limit': '3', 'offset': '2'},
            {'uuid': everyone, 'limit': '2', 'offset': '6', 'direction': 'desc'},
            {'uuid': some, 'offset': '5'},
            {'uuid': f'{some},{some},nope'},
        ]
        for query in queries:
            with self.subTest(query=query):
                assert_that(
                    cached.list_contacts(**listing(**query)),
                    equal_to(live.list_contacts(**listing(**query))),
                )

    def test_a_uuid_listing_sends_no_request_once_the_snapshot_is_loaded(self) -> None:
        plugin = self.make_plugin()
        plugin.list_contacts(**listing())
        self.confd.calls.clear()

        plugin.list_contacts(**listing(uuid=USERS[0]['uuid']))
        plugin.list_contacts(**listing(uuid=f"{USERS[1]['uuid']},{USERS[2]['uuid']}"))

        assert_that(self.confd.calls, empty())

    def test_ttl_0_asks_confd_for_a_uuid_listing(self) -> None:
        plugin = self.make_plugin(ttl=0)
        params = listing(uuid=USERS[0]['uuid'])

        plugin.list_contacts(**params)

        assert_that(self.confd.snapshot_loads(), empty())
        assert_that(
            self.confd.listings(), contains_exactly({'view': 'directory', **params})
        )

    def test_an_unknown_parameter_asks_confd(self) -> None:
        plugin = self.make_plugin()

        plugin.list_contacts(**listing(), context='inside')

        assert_that(self.confd.snapshot_loads(), empty())
        assert_that(
            self.confd.listings(),
            contains_exactly(has_entries(view='directory', context='inside')),
        )

    def test_a_listing_that_cannot_use_the_snapshot_does_not_load_it(self) -> None:
        plugin = self.make_plugin()

        plugin.list_contacts(**listing(search='anna'))

        assert_that(self.confd.snapshot_loads(), empty())

    def test_ttl_0_asks_confd(self) -> None:
        plugin = self.make_plugin(ttl=0)

        plugin.list_contacts(**listing())

        assert_that(self.confd.snapshot_loads(), empty())
        assert_that(self.confd.listings(), has_length(1))

    def test_extra_search_params_ask_confd_for_the_listing(self) -> None:
        plugin = self.make_plugin(extra_search_params={'context': 'inside'})
        params = listing()

        plugin.list_contacts(**params)

        assert_that(self.confd.snapshot_loads(), empty())
        assert_that(
            self.confd.listings(), contains_exactly({'view': 'directory', **params})
        )

    def test_a_failed_first_load_asks_confd_and_waits_a_ttl(self) -> None:
        self.confd.snapshot_failure = ConnectionError('confd is down')
        plugin = self.make_plugin()

        assert_that(self.ids(plugin), contains_exactly(3, 2, 7, 6, 5, 4, 1))
        assert_that(self.ids(plugin), contains_exactly(3, 2, 7, 6, 5, 4, 1))

        assert_that(self.confd.snapshot_loads(), has_length(1))
        assert_that(self.confd.listings(), has_length(2))

    def test_a_confd_failure_is_a_wazo_confd_error(self) -> None:
        plugin = self.make_plugin(ttl=0)
        errors: list[Exception] = [
            ConnectionError('confd is down'),
            HTTPError('500 Server Error'),
            ValueError('not json'),
            TypeError('bad error body'),
        ]
        for error in errors:
            with self.subTest(error=error):
                self.confd.failure = error

                with self.assertRaises(WazoConfdError) as raised:
                    plugin.list_contacts(**listing())

                assert_that(raised.exception.status_code, equal_to(503))
                assert_that(
                    raised.exception.details,
                    has_entries(original_error=str(error)),
                )

    def test_another_error_is_not_hidden(self) -> None:
        plugin = self.make_plugin(ttl=0)
        self.confd.failure = KeyError('a bug')

        with self.assertRaises(KeyError):
            plugin.list_contacts(**listing())
