# Copyright 2014-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from hamcrest import assert_that
from hamcrest import equal_to
from hamcrest import not_
from hamcrest import none
from unittest.mock import Mock
from unittest.mock import patch
from unittest.mock import sentinel

from ..plugin import LookupServicePlugin


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
