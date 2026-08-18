# Copyright 2015-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import time
import unittest
from typing import Any, cast
from unittest.mock import ANY, Mock, patch
from unittest.mock import sentinel as s

from hamcrest import (
    assert_that,
    contains_exactly,
    contains_inanyorder,
    equal_to,
    less_than,
    none,
    not_,
)

from wazo_dird.exception import InvalidContactId
from wazo_dird.helpers import ProfileConfig
from wazo_dird.plugin_manager import ServiceDependencies

from ..plugin import FavoritesServicePlugin, _FavoritesService


def _deps(deps: dict) -> ServiceDependencies:
    return cast(ServiceDependencies, deps)


class TestFavoritesServicePlugin(unittest.TestCase):
    def setUp(self):
        self._config = {}
        self._source_manager = Mock()

    def test_load_no_config(self):
        plugin = FavoritesServicePlugin()

        self.assertRaises(
            ValueError, plugin.load, {'source_manager': self._source_manager}
        )

    def test_load_no_sources(self):
        plugin = FavoritesServicePlugin()

        self.assertRaises(ValueError, plugin.load, {'config': self._config})

    @patch('wazo_dird.plugins.favorites_service.plugin._FavoritesService')
    def test_that_load_returns_a_service(self, MockedFavoritesService):
        plugin = FavoritesServicePlugin()

        service = plugin.load(
            _deps(
                {
                    'source_manager': self._source_manager,
                    'config': self._config,
                    'bus': s.bus,
                    'controller': s.controller,
                }
            )
        )

        assert_that(service, not_(none()))

    @patch('wazo_dird.plugins.favorites_service.plugin._FavoritesService')
    def test_that_load_injects_config_to_the_service(self, MockedFavoritesService):
        plugin = FavoritesServicePlugin()

        service = plugin.load(
            _deps(
                {
                    'config': self._config,
                    'source_manager': self._source_manager,
                    'bus': s.bus,
                    'controller': s.controller,
                }
            )
        )

        MockedFavoritesService.assert_called_once_with(
            self._config, self._source_manager, s.controller, ANY, s.bus
        )
        assert_that(service, equal_to(MockedFavoritesService.return_value))

    def test_no_error_on_unload_not_loaded(self):
        plugin = FavoritesServicePlugin()

        plugin.unload()

    @patch('wazo_dird.plugins.favorites_service.plugin._FavoritesService')
    def test_that_unload_stops_the_services(self, MockedFavoritesService):
        plugin = FavoritesServicePlugin()
        plugin.load(
            _deps(
                {
                    'config': self._config,
                    'source_manager': self._source_manager,
                    'bus': s.bus,
                    'controller': s.controller,
                }
            )
        )

        plugin.unload()

        MockedFavoritesService.return_value.stop.assert_called_once_with()


_SLOW_SOURCE_DELAY = 1.0
_SHORT_TIMEOUT = 0.2


class TestFavoritesServiceTimeout(unittest.TestCase):
    """The favorites service must honour the profile's options.timeout,
    like the lookup and reverse services already do.
    """

    def setUp(self) -> None:
        self._crud = Mock()
        self._crud.get.return_value = [('fast', '1'), ('slow', '2')]
        self._source_manager = Mock()
        self._source_manager.get.side_effect = {
            'fast-uuid': self._new_source('fast', s.fast_result),
            'slow-uuid': self._new_source(
                'slow', s.slow_result, delay=_SLOW_SOURCE_DELAY
            ),
        }.get
        self._service = _FavoritesService(
            {}, self._source_manager, Mock(), self._crud, Mock()
        )

    def tearDown(self) -> None:
        self._service.stop()

    @staticmethod
    def _new_source(name: str, result: Any, delay: float = 0.0) -> Mock:
        source = Mock()
        source.name = name

        def list_(unique_ids: list[str], args: dict[str, Any]) -> list[Any]:
            time.sleep(delay)
            return [result]

        source.list.side_effect = list_
        return source

    @staticmethod
    def _profile_config(**options: Any) -> ProfileConfig:
        return cast(
            'ProfileConfig',
            {
                'name': 'default',
                'services': {
                    'favorites': {
                        'sources': [
                            {'uuid': 'fast-uuid', 'name': 'fast'},
                            {'uuid': 'slow-uuid', 'name': 'slow'},
                        ],
                        'options': options,
                    }
                },
            },
        )

    def test_that_a_source_slower_than_the_timeout_is_left_out(self) -> None:
        profile_config = self._profile_config(timeout=_SHORT_TIMEOUT)

        start = time.monotonic()
        results = self._service.favorites(profile_config, s.user_uuid)
        elapsed = time.monotonic() - start

        assert_that(results, contains_exactly(s.fast_result))
        assert_that(elapsed, less_than(_SLOW_SOURCE_DELAY))

    def test_that_a_source_faster_than_the_timeout_is_returned(self) -> None:
        profile_config = self._profile_config(timeout=_SLOW_SOURCE_DELAY * 10)

        results = self._service.favorites(profile_config, s.user_uuid)

        assert_that(results, contains_inanyorder(s.fast_result, s.slow_result))

    def test_that_no_timeout_waits_for_every_source(self) -> None:
        profile_config = self._profile_config()

        results = self._service.favorites(profile_config, s.user_uuid)

        assert_that(results, contains_inanyorder(s.fast_result, s.slow_result))


class TestNewFavoriteResolvesTheContactId(unittest.TestCase):
    """The backend resolves the contact id before the service stores it."""

    def setUp(self):
        self._crud = Mock()
        self._source_plugin = Mock()
        self._source_manager = Mock()
        self._source_manager.get.return_value = self._source_plugin
        controller = Mock()
        controller.services = {
            'source': Mock(
                list_=Mock(
                    return_value=[
                        {'uuid': s.source_uuid, 'name': 'my_source', 'backend': 'wazo'}
                    ]
                )
            )
        }
        self._service = _FavoritesService(
            {}, self._source_manager, controller, self._crud, Mock()
        )

    def tearDown(self):
        self._service.stop()

    def _new_favorite(self):
        self._service.new_favorite(s.tenant_uuid, 'my_source', 'a-contact-id', s.user)

    def test_the_resolved_contact_id_is_what_gets_stored(self):
        # the database holds the form the source returns, not the one sent
        self._source_plugin.canonical_unique_id.return_value = 'resolved-id'

        self._new_favorite()

        self._source_plugin.canonical_unique_id.assert_called_once_with('a-contact-id')
        self._crud.create.assert_called_once_with(
            s.user, s.tenant_uuid, 'wazo', 'my_source', 'resolved-id'
        )

    def test_a_contact_id_the_source_cannot_resolve_is_not_stored(self):
        self._source_plugin.canonical_unique_id.return_value = None

        self.assertRaises(InvalidContactId, self._new_favorite)

        self._crud.create.assert_not_called()

    def test_a_source_whose_plugin_is_not_loaded_still_accepts(self):
        # favorites() already skips a source with no loaded plugin; a failed
        # plugin must not also make favorites impossible to add
        self._source_manager.get.return_value = None

        self._new_favorite()

        self._crud.create.assert_called_once()
