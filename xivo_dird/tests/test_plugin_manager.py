# -*- coding: utf-8 -*-

# Copyright 2014-2017 The Wazo Authors  (see the AUTHORS file)
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

from unittest import TestCase
from collections import defaultdict

from hamcrest import assert_that, calling, equal_to, has_entries, raises, not_
from mock import ANY, Mock, patch, sentinel as s

from xivo_dird import plugin_manager


class TestPluginManagerServices(TestCase):

    @patch('xivo_dird.plugin_manager.EnabledExtensionManager')
    def test_load_services_loads_service_extensions(self, extension_manager_init):
        extension_manager = extension_manager_init.return_value

        plugin_manager.load_services(s.config, enabled_services=[], sources=s.backends, bus=s.bus)

        extension_manager_init.assert_called_once_with(
            namespace='xivo_dird.services',
            check_func=ANY,
            invoke_on_load=True)
        extension_manager.map.assert_called_once_with(plugin_manager.load_service_extension,
                                                      s.config,
                                                      s.backends,
                                                      s.bus)

    @patch('xivo_dird.plugin_manager.EnabledExtensionManager')
    def test_load_services_returns_dict_of_callables(self, extension_manager_init):
        extension_manager = extension_manager_init.return_value
        extension_manager.map.return_value = [(s.name1, s.callable1), (s.name2, s.callable2)]

        result = plugin_manager.load_services(s.config,
                                              enabled_services=[],
                                              sources=s.backends,
                                              bus=s.bus)

        assert_that(result, has_entries({s.name1: s.callable1, s.name2: s.callable2}))

    def test_load_service_extension_passes_right_plugin_arguments(self):
        extension = Mock()

        plugin_manager.load_service_extension(extension, s.config, s.sources, s.bus)

        extension.obj.load.assert_called_once_with({
            'config': s.config,
            'sources': s.sources,
            'bus': s.bus,
        })

    def test_load_service_extension_returns_extension_name_and_result_from_load(self):
        extension = Mock()
        extension.name = s.name
        extension.obj.load.return_value = s.callable
        config = defaultdict(Mock)

        result = plugin_manager.load_service_extension(extension, config, s.sources, s.bus)

        assert_that(result, equal_to((extension.name, s.callable)))

    def test_unload_services_calls_unload_on_services(self):
        plugin_manager.services_extension_manager = Mock()

        plugin_manager.unload_services()

        plugin_manager.services_extension_manager.map_method.assert_called_once_with('unload')

    def test_that_unload_services_does_nothing_when_load_services_has_not_been_run(self):
        with patch('xivo_dird.plugin_manager.services_extension_manager', None):
            assert_that(calling(plugin_manager.unload_services),
                        not_(raises(Exception)))


class TestPluginManagerSources(TestCase):

    def tearDown(self):
        plugin_manager.source_manager = None

    @patch('xivo_dird.plugin_manager.SourceManager')
    def test_load_sources_calls_source_manager(self, source_manager_init):
        source_manager = source_manager_init.return_value

        plugin_manager.load_sources(s.enabled, s.source_config_dir)

        source_manager_init.assert_called_once_with(s.enabled, s.source_config_dir)
        source_manager.load_sources.assert_called_once_with()

    @patch('xivo_dird.plugin_manager.SourceManager')
    def test_load_sources_returns_result_from_source_manager_load(self, source_manager_init):
        source_manager = source_manager_init.return_value
        source_manager.load_sources.return_value = s.result

        result = plugin_manager.load_sources(s.enabled, s.source_config_dir)

        assert_that(result, equal_to(s.result))


class TestPluginManagerViews(TestCase):

    @patch('xivo_dird.plugin_manager.EnabledExtensionManager')
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
            'rest_api': rest_api.api,
            'services': s.services,
        })
