# Copyright 2014-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from concurrent.futures import ALL_COMPLETED
from typing import cast
from unittest.mock import Mock, patch, sentinel

from hamcrest import assert_that, equal_to, none, not_

from wazo_dird.helpers import ProfileConfig
from wazo_dird.plugin_manager import ServiceDependencies

from ..plugin import LookupServicePlugin, _LookupService


def _deps(deps: dict) -> ServiceDependencies:
    return cast(ServiceDependencies, deps)


class TestLookupServicePlugin(unittest.TestCase):
    def setUp(self):
        self._source_manager = Mock()

    def test_load_no_config(self):
        plugin = LookupServicePlugin()

        self.assertRaises(
            ValueError, plugin.load, {'source_manager': self._source_manager}
        )

    def test_load_no_sources(self):
        plugin = LookupServicePlugin()

        self.assertRaises(ValueError, plugin.load, {'config': sentinel.sources})

    @patch('wazo_dird.plugins.lookup_service.plugin._LookupService')
    def test_that_load_returns_a_service(self, MockedLookupService):
        plugin = LookupServicePlugin()

        service = plugin.load(
            _deps(
                {
                    'source_manager': self._source_manager,
                    'config': sentinel.config,
                    'controller': sentinel.controller,
                }
            )
        )

        assert_that(service, not_(none()))

    @patch('wazo_dird.plugins.lookup_service.plugin._LookupService')
    def test_that_load_injects_config_to_the_service(self, MockedLookupService):
        plugin = LookupServicePlugin()

        service = plugin.load(
            _deps(
                {
                    'config': sentinel.config,
                    'source_manager': self._source_manager,
                    'controller': sentinel.controller,
                }
            )
        )

        MockedLookupService.assert_called_once_with(
            sentinel.config, self._source_manager, sentinel.controller
        )
        assert_that(service, equal_to(MockedLookupService.return_value))

    def test_no_error_on_unload_not_loaded(self):
        plugin = LookupServicePlugin()

        plugin.unload()

    @patch('wazo_dird.plugins.lookup_service.plugin._LookupService')
    def test_that_unload_stops_the_services(self, MockedLookupService):
        plugin = LookupServicePlugin()
        plugin.load(
            _deps(
                {
                    'config': sentinel.config,
                    'source_manager': self._source_manager,
                    'controller': sentinel.controller,
                }
            )
        )

        plugin.unload()

        MockedLookupService.return_value.stop.assert_called_once_with()


def _make_lookup_service() -> _LookupService:
    source_manager = Mock()
    source_manager.get.return_value = None
    return _LookupService(config={}, source_manager=source_manager, controller=Mock())


class TestLookupNullOptions(unittest.TestCase):
    @patch('wazo_dird.plugins.lookup_service.plugin.wait')
    def test_null_options_does_not_crash(self, mock_wait):
        mock_wait.return_value = ([], [])
        service = _make_lookup_service()
        profile = {
            'name': 'test',
            'services': {'lookup': {'sources': [], 'options': None}},
        }

        service.lookup(cast(ProfileConfig, profile), 'tenant', 'alice', 'user-uuid')

        mock_wait.assert_called_once_with([], return_when=ALL_COMPLETED)
