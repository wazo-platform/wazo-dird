# Copyright 2014-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import time
import unittest
from unittest.mock import Mock, patch, sentinel

from hamcrest import assert_that, contains_string, equal_to, none, not_

from ..plugin import LookupServicePlugin, _LookupService


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
            {
                'source_manager': self._source_manager,
                'config': sentinel.config,
                'controller': sentinel.controller,
            }
        )

        assert_that(service, not_(none()))

    @patch('wazo_dird.plugins.lookup_service.plugin._LookupService')
    def test_that_load_injects_config_to_the_service(self, MockedLookupService):
        plugin = LookupServicePlugin()

        service = plugin.load(
            {
                'config': sentinel.config,
                'source_manager': self._source_manager,
                'controller': sentinel.controller,
            }
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
            {
                'config': sentinel.config,
                'source_manager': self._source_manager,
                'controller': sentinel.controller,
            }
        )

        plugin.unload()

        MockedLookupService.return_value.stop.assert_called_once_with()


class TestLookupServiceBackendStats(unittest.TestCase):
    def setUp(self):
        self._source_manager = Mock()
        self._service = _LookupService({}, self._source_manager, sentinel.controller)

    def tearDown(self):
        self._service.stop()

    def test_that_timed_out_backends_are_logged_with_inf_duration(self):
        fast = Mock()
        fast.name = 'fast'
        fast.search.return_value = [{'firstname': 'Alice'}]
        slow = Mock()
        slow.name = 'slow'

        def slow_search(term, args):
            time.sleep(0.5)
            return []

        slow.search.side_effect = slow_search
        sources = {'fast-uuid': fast, 'slow-uuid': slow}
        self._source_manager.get.side_effect = sources.get
        profile_config = {
            'name': 'default',
            'services': {
                'lookup': {
                    'sources': [{'uuid': 'fast-uuid'}, {'uuid': 'slow-uuid'}],
                    'timeout': 0.1,
                }
            },
        }

        with self.assertLogs(
            'wazo_dird.plugins.lookup_service.plugin', level='INFO'
        ) as logs:
            results = self._service.lookup(
                profile_config, sentinel.tenant_uuid, 'term', sentinel.user_uuid
            )

        log_output = '\n'.join(logs.output)
        assert_that(log_output, contains_string('fast results=1'))
        assert_that(log_output, contains_string('slow results=0 duration_ms=inf'))
        assert_that(results, equal_to([{'firstname': 'Alice'}]))
