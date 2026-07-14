# Copyright 2014-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from concurrent.futures import ALL_COMPLETED
from typing import cast
from unittest.mock import Mock, patch, sentinel

from hamcrest import assert_that, contains_string, equal_to, none, not_

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


TIMING_LOGGER = 'wazo_dird.plugins.lookup_service.plugin.timing'


class TestLookupPerSourceTiming(unittest.TestCase):
    def _service_with_source(self, source: Mock) -> _LookupService:
        source_manager = Mock()
        source_manager.get.return_value = source
        return _LookupService(
            config={}, source_manager=source_manager, controller=Mock()
        )

    def test_logs_queue_and_exec_time_per_source(self):
        source = Mock()
        source.name = 'my_ldap'
        source.backend = 'ldap'
        source.search.return_value = [sentinel.result1, sentinel.result2]
        service = self._service_with_source(source)
        profile = {
            'name': 'test',
            'services': {'lookup': {'sources': [{'uuid': 'src-uuid'}]}},
        }

        with self.assertLogs(TIMING_LOGGER, level='DEBUG') as logs:
            results = service.lookup(
                cast(ProfileConfig, profile), 'tenant', 'alice', 'user-uuid'
            )

        assert_that(results, equal_to([sentinel.result1, sentinel.result2]))
        messages = [r.getMessage() for r in logs.records if 'my_ldap' in r.getMessage()]
        assert_that(len(messages), equal_to(1))
        assert_that(messages[0], contains_string('backend=ldap'))
        assert_that(messages[0], contains_string('queue_ms='))
        assert_that(messages[0], contains_string('exec_ms='))
        assert_that(messages[0], contains_string('results=2'))
