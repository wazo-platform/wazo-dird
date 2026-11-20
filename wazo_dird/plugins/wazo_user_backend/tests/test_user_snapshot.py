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
from .confd_fake import FakeConfd, make_user

SOURCE_CONFIG = {
    'uuid': 'ae086548-2d36-4367-8914-8dfcd8645ca7',
    'backend': 'wazo',
    'tenant_uuid': '02153e33-4b59-4a9f-8cd1-7e917b306e1d',
    'confd': {},
    'auth': {},
    'name': 'my_test_xivo',
    'searched_columns': ['firstname', 'lastname', 'full_name'],
}


USERS = [
    make_user(1, 'Zoe', 'Zimmer', '1001'),
    make_user(2, 'Paul', 'àccent', '1002'),
    make_user(3, 'Louis-Jean', '', '1003'),
    make_user(4, 'Anna', 'Alvarez', '1004'),
]


class TestUserSnapshot(unittest.TestCase):
    def setUp(self) -> None:
        self.confd = FakeConfd(USERS)
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
            'main_config': main_config,
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

    def test_search_orders_users_as_confd_does_with_an_empty_lastname(self) -> None:
        live = self.make_plugin({'wazo_user_cache_ttl': 0})
        cached = self.make_plugin({})

        # by lastname without case nor accents, the users without one last
        assert_that(self.ids(cached, ''), contains_exactly(4, 2, 1, 3))
        assert_that(self.ids(live, ''), contains_exactly(4, 2, 1, 3))

        self.confd.users.append({**USERS[0], 'id': 5, 'uuid': 'u5', 'lastname': None})
        self.now += 100
        assert_that(self.ids(cached, '')[-2:], contains_exactly(3, 5))

    def test_search_does_not_ask_confd_once_loaded(self) -> None:
        plugin = self.make_plugin({})
        plugin.search('paul')
        self.confd.calls.clear()

        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        assert_that(self.confd.calls, empty())

    def test_search_finds_an_accented_name_with_an_unaccented_term(self) -> None:
        plugin = self.make_plugin({})

        assert_that(self.ids(plugin, 'accent'), contains_exactly(2))

    def test_the_snapshot_is_one_request_without_paging_nor_order(self) -> None:
        plugin = self.make_plugin({})
        plugin.search('paul')

        assert_that(
            self.confd.snapshot_loads(),
            contains_exactly({'view': 'directory', 'recurse': True}),
        )
        assert_that(self.confd.calls, has_length(1))

    def test_the_snapshot_is_sorted_whatever_the_order_confd_answers(self) -> None:
        users_list = self.confd.users_list

        def newest_first(**params: Any) -> dict[str, Any]:
            result = users_list(**params)
            items = sorted(result['items'], key=lambda u: u['id'], reverse=True)
            return {**result, 'items': items}

        self.client.users.list.side_effect = newest_first
        plugin = self.make_plugin({})

        assert_that(self.ids(plugin, ''), contains_exactly(4, 2, 1, 3))

    def test_thousands_of_users_load_in_one_request(self) -> None:
        self.confd.users = [
            make_user(i, 'First', f'Last{i:05d}', str(20000 + i)) for i in range(5000)
        ]
        plugin = self.make_plugin({})

        assert_that(self.ids(plugin, 'last04999'), contains_exactly(4999))
        assert_that(self.ids(plugin, 'first'), has_length(5000))

        assert_that(self.confd.calls, has_length(1))

    def test_a_missing_ttl_key_uses_the_default_ttl(self) -> None:
        plugin = self.make_plugin({})
        plugin.search('paul')
        self.confd.users.append(make_user(5, 'Paula', 'New', '1005'))

        self.now += 59
        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        self.now += 2
        assert_that(self.ids(plugin, 'paul'), contains_inanyorder(2, 5))
        assert_that(self.confd.searched(), has_length(0))

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
        self.confd.snapshot_failure = ConnectionError('confd is down')
        self.now += 61

        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        self.now += 30
        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        assert_that(self.confd.snapshot_loads(), has_length(2))
        self.now += 31
        self.ids(plugin, 'paul')
        assert_that(self.confd.snapshot_loads(), has_length(3))

    def test_a_failed_first_load_asks_confd(self) -> None:
        self.confd.snapshot_failure = ConnectionError('confd is down')
        plugin = self.make_plugin({})

        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        assert_that(self.confd.searched(), has_length(1))

    def test_a_lookup_during_a_load_asks_confd(self) -> None:
        self.confd.gate = threading.Event()
        plugin = self.make_plugin({})
        loader = threading.Thread(target=plugin.search, args=('paul',))
        loader.start()
        for _ in range(500):
            if self.confd.snapshot_loads():
                break
            loader.join(0.01)

        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        assert_that(self.confd.searched(), has_length(1))
        self.confd.gate.set()
        loader.join(5)
        assert_that(self.confd.snapshot_loads(), has_length(1))

    def test_ttl_0_never_builds_a_snapshot(self) -> None:
        plugin = self.make_plugin({'wazo_user_cache_ttl': 0})

        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        assert_that(self.confd.snapshot_loads(), empty())
        assert_that(self.confd.searched(), has_length(1))

    def test_extra_search_params_turn_the_cache_off_with_a_warning(self) -> None:
        with self.assertLogs(
            'wazo_dird.plugins.wazo_user_backend.plugin', 'WARNING'
        ) as logs:
            plugin = self.make_plugin({}, extra_search_params={'context': 'inside'})

        assert_that(
            logs.output,
            contains_exactly(
                'WARNING:wazo_dird.plugins.wazo_user_backend.plugin:'
                'my_test_xivo: extra_search_params disable the user cache'
            ),
        )
        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        assert_that(
            self.confd.searched(),
            contains_exactly(has_entries(context='inside', search='paul')),
        )
        assert_that(self.confd.snapshot_loads(), empty())

    def test_extra_search_params_load_with_a_ttl_of_0(self) -> None:
        plugin = self.make_plugin(
            {'wazo_user_cache_ttl': 0}, extra_search_params={'context': 'inside'}
        )

        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        assert_that(
            self.confd.searched(),
            contains_exactly(has_entries(context='inside', search='paul')),
        )
        assert_that(self.confd.snapshot_loads(), empty())

    def test_no_extra_search_params_load_with_a_ttl(self) -> None:
        configs: list[dict[str, Any]] = [{}, {'extra_search_params': {}}]
        for config in configs:
            with self.subTest(config=config):
                plugin = self.make_plugin({}, **config)

                assert_that(self.ids(plugin, 'paul'), contains_exactly(2))

    def test_a_load_longer_than_the_ttl_still_leaves_a_fresh_snapshot(self) -> None:
        plugin = self.make_plugin({'wazo_user_cache_ttl': 60})
        users_list = self.confd.users_list

        def slow_load(**params: Any) -> dict[str, Any]:
            self.now += 100
            return users_list(**params)

        self.client.users.list.side_effect = slow_load
        self.ids(plugin, 'paul')
        self.confd.calls.clear()

        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))

        assert_that(self.confd.calls, empty())

    def test_a_failed_load_longer_than_the_ttl_is_not_retried_at_once(self) -> None:
        plugin = self.make_plugin({'wazo_user_cache_ttl': 60})

        def slow_failure(**params: Any) -> dict[str, Any]:
            if 'search' not in params:
                self.now += 100
            raise ConnectionError('confd is down')

        self.client.users.list.side_effect = slow_failure
        self.ids(plugin, 'paul')
        self.client.users.list.side_effect = self.confd.users_list
        self.confd.calls.clear()

        self.ids(plugin, 'paul')

        assert_that(self.confd.snapshot_loads(), empty())

    def test_a_ttl_written_as_a_number_in_text_is_read_as_a_number(self) -> None:
        plugin = self.make_plugin({'wazo_user_cache_ttl': '30'})
        self.ids(plugin, 'paul')
        self.confd.calls.clear()

        self.now += 29
        self.ids(plugin, 'paul')
        assert_that(self.confd.calls, empty())
        self.now += 2
        self.ids(plugin, 'paul')

        assert_that(self.confd.snapshot_loads(), has_length(1))

    def test_a_ttl_below_a_second_is_accepted(self) -> None:
        plugin = self.make_plugin({'wazo_user_cache_ttl': 0.5})
        self.ids(plugin, 'paul')
        self.confd.calls.clear()

        self.now += 0.4
        self.ids(plugin, 'paul')
        assert_that(self.confd.calls, empty())
        self.now += 0.2
        self.ids(plugin, 'paul')

        assert_that(self.confd.snapshot_loads(), has_length(1))

    def test_a_negative_or_empty_ttl_turns_the_cache_off(self) -> None:
        for ttl in (-5, '-1', None, '', 0):
            with self.subTest(ttl=ttl):
                self.confd.calls.clear()
                plugin = self.make_plugin({'wazo_user_cache_ttl': ttl})

                assert_that(self.ids(plugin, 'paul'), contains_exactly(2))

                assert_that(self.confd.snapshot_loads(), empty())
                assert_that(self.confd.searched(), has_length(1))

    def test_a_ttl_that_is_not_a_number_fails_once_at_load(self) -> None:
        plugin = WazoUserPlugin()
        dependencies = {
            'config': SOURCE_CONFIG,
            'main_config': {'wazo_user_cache_ttl': 'abc'},
            'auth_client': Mock(),
            'token_renewer': Mock(),
        }
        with patch('wazo_dird.plugins.wazo_user_backend.plugin.registry') as registry:
            registry.get.return_value = self.client
            with self.assertRaises(ValueError):
                plugin.load(cast(SourcePluginDependencies, dependencies))

        # the source manager keeps the plugin: it works, on the confd path
        assert_that(self.ids(plugin, 'paul'), contains_exactly(2))
        assert_that(self.confd.snapshot_loads(), empty())
        assert_that(self.confd.searched(), has_length(1))

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

        assert_that(self.confd.snapshot_loads(), empty())
        lock.release.assert_called_once_with()
