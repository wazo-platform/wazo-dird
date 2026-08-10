# Copyright 2015-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import time
import unittest
from unittest.mock import ANY, Mock, patch
from unittest.mock import sentinel as s

from hamcrest import assert_that, contains_string, equal_to, none, not_

from ..plugin import FavoritesServicePlugin, _FavoritesService


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
            {
                'source_manager': self._source_manager,
                'config': self._config,
                'bus': s.bus,
                'controller': s.controller,
            }
        )

        assert_that(service, not_(none()))

    @patch('wazo_dird.plugins.favorites_service.plugin._FavoritesService')
    def test_that_load_injects_config_to_the_service(self, MockedFavoritesService):
        plugin = FavoritesServicePlugin()

        service = plugin.load(
            {
                'config': self._config,
                'source_manager': self._source_manager,
                'bus': s.bus,
                'controller': s.controller,
            }
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
            {
                'config': self._config,
                'source_manager': self._source_manager,
                'bus': s.bus,
                'controller': s.controller,
            }
        )

        plugin.unload()

        MockedFavoritesService.return_value.stop.assert_called_once_with()


class TestFavoritesServiceBackendStats(unittest.TestCase):
    def setUp(self):
        self._source_manager = Mock()
        self._crud = Mock()
        self._service = _FavoritesService(
            {'lookup_timeout': 0.1, 'uuid': 'xivo-uuid'},
            self._source_manager,
            s.controller,
            self._crud,
            s.bus,
        )

    def tearDown(self):
        self._service.stop()

    def test_that_timed_out_backends_are_logged_with_inf_duration(self):
        fast = Mock()
        fast.name = 'fast'
        fast.list.return_value = [{'firstname': 'Alice'}]
        slow = Mock()
        slow.name = 'slow'

        def slow_list(contact_ids, args):
            time.sleep(0.5)
            return []

        slow.list.side_effect = slow_list
        sources = {'fast-uuid': fast, 'slow-uuid': slow}
        self._source_manager.get.side_effect = sources.get
        self._crud.get.return_value = [('fast', '1'), ('slow', '2')]
        profile_config = {
            'name': 'default',
            'services': {
                'favorites': {
                    'sources': [
                        {'name': 'fast', 'uuid': 'fast-uuid'},
                        {'name': 'slow', 'uuid': 'slow-uuid'},
                    ],
                }
            },
        }

        with self.assertLogs(
            'wazo_dird.plugins.favorites_service.plugin', level='INFO'
        ) as logs:
            results = self._service.favorites(profile_config, s.user_uuid)

        log_output = '\n'.join(logs.output)
        assert_that(log_output, contains_string('fast results=1'))
        assert_that(log_output, contains_string('slow results=0 duration_ms=inf'))
        assert_that(results, equal_to([{'firstname': 'Alice'}]))
