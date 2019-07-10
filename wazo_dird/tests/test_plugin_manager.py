# Copyright 2014-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase

from hamcrest import assert_that, calling, not_, raises
from mock import Mock, patch

from wazo_dird import plugin_manager


class TestPluginManagerServices(TestCase):
    def test_unload_services_calls_unload_on_services(self):
        plugin_manager.services_extension_manager = Mock()

        plugin_manager.unload_services()

        plugin_manager.services_extension_manager.map_method.assert_called_once_with(
            'unload'
        )

    def test_that_unload_services_does_nothing_when_load_services_has_not_been_run(
        self
    ):
        with patch('wazo_dird.plugin_manager.services_extension_manager', None):
            assert_that(
                calling(plugin_manager.unload_services), not_(raises(Exception))
            )
