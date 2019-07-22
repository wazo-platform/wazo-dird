# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from hamcrest import assert_that, equal_to, not_, none
from mock import ANY, Mock, patch, sentinel as s

from ..plugin import FavoritesServicePlugin


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

    def test_that_load_returns_a_service(self):
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
