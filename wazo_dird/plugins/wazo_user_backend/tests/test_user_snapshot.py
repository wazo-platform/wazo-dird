# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import threading
import unittest
from typing import Any, cast
from unittest.mock import Mock, patch

from hamcrest import (
    assert_that,
    contains_exactly,
    contains_inanyorder,
    empty,
    equal_to,
    has_entries,
    has_length,
)
from requests.exceptions import ConnectionError

from wazo_dird.plugins.base_plugins import SourcePluginDependencies

from ..plugin import WazoUserPlugin

SOURCE_CONFIG = {
    'uuid': 'ae086548-2d36-4367-8914-8dfcd8645ca7',
    'backend': 'wazo',
    'tenant_uuid': '02153e33-4b59-4a9f-8cd1-7e917b306e1d',
    'confd': {},
    'auth': {},
    'name': 'my_test_xivo',
    'searched_columns': ['firstname', 'lastname', 'full_name'],
}


def make_user(
    user_id: int, firstname: str, lastname: str, exten: str
) -> dict[str, Any]:
    return {
        'id': user_id,
        'uuid': f'00000000-0000-0000-0000-{user_id:012d}',
        'agent_id': None,
        'line_id': 100 + user_id,
        'firstname': firstname,
        'lastname': lastname,
        'exten': exten,
        'email': None,
        'mobile_phone_number': None,
        'voicemail_number': None,
        'userfield': None,
        'description': None,
    }


USERS = [
    make_user(1, 'Zoe', 'Zimmer', '1001'),
    make_user(2, 'Paul', 'àccent', '1002'),
    make_user(3, 'Louis-Jean', '', '1003'),
    make_user(4, 'Anna', 'Alvarez', '1004'),
]


class FakeConfd:
    """GET /users like confd: ILIKE `search`, ordered by lastname or `order`."""

    def __init__(self) -> None:
        self.users = list(USERS)
        self.calls: list[dict[str, Any]] = []
        self.failing = False
        self.gate: threading.Event | None = None

    def infos(self) -> dict[str, str]:
        return {'uuid': 'my-xivo-uuid'}

    def users_list(self, **params: Any) -> dict[str, Any]:
        self.calls.append(params)
        if 'limit' in params:
            if self.gate is not None:
                assert self.gate.wait(10)
            if self.failing:
                raise ConnectionError('confd is down')
        items = list(self.users)
        if params.get('search'):
            needle = params['search'].lower()
            items = [
                u
                for u in items
                if needle in f"{u['firstname']} {u['lastname']} {u['exten']}".lower()
            ]
        items.sort(
            key=lambda u: u['id']
            if params.get('order') == 'id'
            else u['lastname'].lower()
        )
        offset = params.get('offset', 0)
        page = items[offset : offset + params['limit']] if 'limit' in params else items
        return {'items': page, 'total': len(items)}

    def paged(self) -> list[dict[str, Any]]:
        return [call for call in self.calls if 'limit' in call]

    def searched(self) -> list[dict[str, Any]]:
        return [call for call in self.calls if 'search' in call]


class TestUserSnapshot(unittest.TestCase):
    def setUp(self) -> None:
        self.confd = FakeConfd()
        self.client = Mock()
        self.client.users.list.side_effect = self.confd.users_list
        self.client.infos.side_effect = self.confd.infos
        self.now = 1000.0
        patcher = patch(
            'wazo_dird.plugins.wazo_user_backend.plugin.monotonic', lambda: self.now
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self) -> None:
        if self.confd.gate is not None:
            self.confd.gate.set()

    def make_plugin(self, main_config: dict[str, Any], **config: Any) -> WazoUserPlugin:
        dependencies = {
            'config': {**SOURCE_CONFIG, **config},
            'main_config': {'wazo_user_cache_ttl': 60, **main_config},
            'auth_client': Mock(),
            'token_renewer': Mock(),
        }
        plugin = WazoUserPlugin()
        with patch('wazo_dird.plugins.wazo_user_backend.plugin.registry') as registry:
            registry.get.return_value = self.client
            plugin.load(cast(SourcePluginDependencies, dependencies))
        return plugin

    def ids(self, plugin: WazoUserPlugin, term: str) -> list[Any]:
        return [result.fields['id'] for result in plugin.search(term)]

    def test_search_gives_the_same_users_as_asking_confd(self) -> None:
        for columns in (
            ['firstname', 'lastname', 'full_name'],
            ['lastname'],
            ['exten'],
        ):
            live = self.make_plugin(
                {'wazo_user_cache_ttl': 0}, searched_columns=columns
            )
            cached = self.make_plugin(
                {'wazo_user_cache_ttl': 60}, searched_columns=columns
            )
            for term in [
                'paul',
                'PAUL',
                'Paul à',
                'àccent',
                'louis',
                'zimmer',
                '1002',
                '',
                'zzz',
            ]:
                with self.subTest(columns=columns, term=term):
                    assert_that(cached.search(term), equal_to(live.search(term)))

    def test_search_does_not_ask_confd_once_loaded(self) -> None:
        plugin = self.make_plugin({})
        plugin.search('paul')
        self.confd.calls.clear()

        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        assert_that(self.confd.calls, empty())

    def test_search_finds_an_accented_name_with_an_unaccented_term(self) -> None:
        plugin = self.make_plugin({})

        assert_that(self.ids(plugin, 'accent'), contains_exactly(2))

    def test_the_snapshot_is_loaded_in_pages_of_1000_users(self) -> None:
        plugin = self.make_plugin({})
        plugin.search('paul')

        assert_that(
            self.confd.paged(),
            contains_exactly(
                {
                    'view': 'directory',
                    'recurse': True,
                    'order': 'id',
                    'limit': 1000,
                    'offset': 0,
                }
            ),
        )

    def test_expiry_reloads_the_snapshot(self) -> None:
        plugin = self.make_plugin({'wazo_user_cache_ttl': 60})
        plugin.search('paul')
        self.confd.users.append(make_user(5, 'Paula', 'New', '1005'))

        self.now += 59
        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        self.now += 2
        assert_that(self.ids(plugin, 'paul'), contains_inanyorder(2, 5))

    def test_a_failed_reload_keeps_the_old_snapshot_until_the_next_ttl(self) -> None:
        plugin = self.make_plugin({'wazo_user_cache_ttl': 60})
        plugin.search('paul')
        self.confd.failing = True
        self.now += 61

        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        self.now += 30
        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        assert_that(self.confd.paged(), has_length(2))
        self.now += 31
        self.ids(plugin, 'paul')
        assert_that(self.confd.paged(), has_length(3))

    def test_a_failed_first_load_asks_confd(self) -> None:
        self.confd.failing = True
        plugin = self.make_plugin({})

        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        assert_that(self.confd.searched(), has_length(1))

    def test_a_lookup_during_a_load_asks_confd(self) -> None:
        self.confd.gate = threading.Event()
        plugin = self.make_plugin({})
        loader = threading.Thread(target=plugin.search, args=('paul',))
        loader.start()
        for _ in range(500):
            if self.confd.paged():
                break
            loader.join(0.01)

        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        assert_that(self.confd.searched(), has_length(1))
        self.confd.gate.set()
        loader.join(5)
        assert_that(self.confd.paged(), has_length(1))

    def test_a_confd_ignoring_the_offset_does_not_loop_forever(self) -> None:
        # a page that adds no user ends the load, whatever `total` claims
        def ignore_offset(**params: Any) -> dict[str, Any]:
            self.confd.calls.append(params)
            assert len(self.confd.calls) < 20, 'the load does not stop'
            return {'items': USERS[:2], 'total': 10}

        self.client.users.list.side_effect = ignore_offset
        plugin = self.make_plugin({})

        assert_that(self.ids(plugin, ''), contains_inanyorder(1, 2))
        assert_that(self.confd.calls, has_length(2))

    def test_ttl_0_never_builds_a_snapshot(self) -> None:
        plugin = self.make_plugin({'wazo_user_cache_ttl': 0})

        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        assert_that(self.confd.paged(), empty())
        assert_that(self.confd.searched(), has_length(1))

    def test_extra_search_params_do_not_stop_the_snapshot(self) -> None:
        for extra in ({'limit': 5}, {'order': 'firstname'}, {'offset': 3}):
            with self.subTest(extra=extra):
                self.confd.calls.clear()
                plugin = self.make_plugin({}, extra_search_params=extra)

                assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
                assert_that(self.confd.searched(), empty())
                assert_that(
                    self.confd.paged(),
                    contains_exactly(
                        has_entries(order='id', limit=1000, offset=0, view='directory')
                    ),
                )

    def test_a_lookup_that_lost_the_race_does_not_reload(self) -> None:
        # B saw the snapshot expired, A reloaded it, then B got the lock
        plugin = self.make_plugin({})
        real_acquire = plugin._refresh_lock.acquire

        def acquire_after_a_reload(blocking: bool = True) -> bool:
            plugin._snapshot_expires = self.now + 60
            return real_acquire(blocking)

        lock = Mock(wraps=plugin._refresh_lock)
        lock.acquire.side_effect = acquire_after_a_reload
        plugin._refresh_lock = lock

        self.ids(plugin, 'paul')

        assert_that(self.confd.paged(), empty())
        lock.release.assert_called_once_with()
