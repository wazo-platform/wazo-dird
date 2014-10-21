# -*- coding: utf-8 -*-

# Copyright (C) 2014 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

from hamcrest import assert_that, equal_to
from mock import ANY, Mock, patch, sentinel as s
from unittest import TestCase

from xivo_dird.core import plugin_manager


class TestPluginManagerServices(TestCase):

    @patch('stevedore.enabled.EnabledExtensionManager')
    def test_load_services_loads_service_extensions(self, extension_manager_init):
        extension_manager = extension_manager_init.return_value

        plugin_manager.load_services(s.config, enabled_services=[], sources=s.backends)

        extension_manager_init.assert_called_once_with(
            namespace='xivo_dird.services',
            check_func=ANY,
            invoke_on_load=True)
        extension_manager.map.assert_called_once_with(plugin_manager.load_service_extension,
                                                      s.config,
                                                      s.backends)

    def test_load_service_extension_passes_right_plugin_arguments(self):
        extension = Mock()
        extension.name = 'my_plugin'
        config = {
            'my_plugin': s.plugin_config
        }

        plugin_manager.load_service_extension(extension, config, s.sources)

        extension.obj.load.assert_called_once_with({
            'config': s.plugin_config,
            'sources': s.sources
        })

    def test_unload_services_calls_unload_on_services(self):
        plugin_manager.extension_manager = Mock()

        plugin_manager.unload_services()

        plugin_manager.extension_manager.map_method.assert_called_once_with('unload')


class TestPluginManagerSources(TestCase):

    @patch('xivo_dird.core.plugin_manager.SourceManager')
    def test_load_sources_calls_source_manager(self, source_manager_init):
        source_manager = source_manager_init.return_value
        expected_config = {
            'source_plugins': s.enabled,
            'plugin_config_dir': s.source_config_dir,
        }

        plugin_manager.load_sources(s.enabled, s.source_config_dir)

        source_manager_init.assert_called_once_with(expected_config)
        source_manager.load_sources.assert_called_once_with()

    @patch('xivo_dird.core.plugin_manager.SourceManager')
    def test_load_sources_returns_result_from_source_manager_load(self, source_manager_init):
        source_manager = source_manager_init.return_value
        source_manager.load_sources.return_value = s.result

        result = plugin_manager.load_sources(s.enabled, s.source_config_dir)

        assert_that(result, equal_to(s.result))


class TestPluginManagerViews(TestCase):

    @patch('stevedore.enabled.EnabledExtensionManager')
    def test_load_views_loads_view_extensions(self, extension_manager_init):
        extension_manager = extension_manager_init.return_value

        plugin_manager.load_views(s.config, enabled_views=[], services=s.services, rest_api=s.rest_api)

        extension_manager_init.assert_called_once_with(
            namespace='xivo_dird.views',
            check_func=ANY,
            invoke_on_load=True)
        extension_manager.map.assert_called_once_with(plugin_manager.load_view_extension,
                                                      s.config,
                                                      s.services,
                                                      s.rest_api)

    def test_load_view_extension_passes_right_plugin_arguments(self):
        extension = Mock()
        extension.name = 'my_plugin'
        rest_api = Mock()

        plugin_manager.load_view_extension(extension, s.config, s.services, rest_api)

        extension.obj.load.assert_called_once_with({
            'config': s.config,
            'http_app': rest_api.app,
            'services': s.services,
        })
