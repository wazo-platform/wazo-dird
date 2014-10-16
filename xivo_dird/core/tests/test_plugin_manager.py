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


class TestPluginManager(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch('stevedore.enabled.EnabledExtensionManager')
    def test_load_services_loads_service_extensions(self, extension_manager_init):
        rest_api = Mock()
        extension_manager = extension_manager_init.return_value

        plugin_manager.load_services(s.config, rest_api)

        extension_manager_init.assert_called_once_with(
            namespace='xivo_dird.services',
            check_func=ANY,
            invoke_on_load=True)
        extension_manager.map.assert_called_once_with(plugin_manager.load_service_extension,
                                                      s.config,
                                                      rest_api)

    def test_load_service_extension_passes_right_plugin_arguments(self):
        extension = Mock()
        extension.name = 'my_plugin'
        rest_api = Mock()
        config = {
            'my_plugin': s.plugin_config
        }

        plugin_manager.load_service_extension(extension, config, rest_api)

        extension.obj.load.assert_called_once_with({
            'http_app': rest_api.app,
            'http_namespace': rest_api.namespace,
            'http_api': rest_api.api,
            'config': s.plugin_config
        })

    def test_services_filter_when_service_not_in_config_then_false(self):
        config = {}
        extension = Mock()

        result = plugin_manager.services_filter(config, extension)

        assert_that(result, equal_to(False))

    def test_services_filter_when_service_in_config_then_not_enabled_by_default(self):
        config = {'my_plugin': {}}
        extension = Mock()
        extension.name = 'my_plugin'

        result = plugin_manager.services_filter(config, extension)

        assert_that(result, equal_to(False))

    def test_services_filter_when_service_in_config_and_not_enabled_then_not_enabled(self):
        config = {'my_plugin': {'enabled': False}}
        extension = Mock()
        extension.name = 'my_plugin'

        result = plugin_manager.services_filter(config, extension)

        assert_that(result, equal_to(False))

    def test_services_filter_when_service_in_config_and_enabled_then_enabled(self):
        config = {'my_plugin': {'enabled': True}}
        extension = Mock()
        extension.name = 'my_plugin'

        result = plugin_manager.services_filter(config, extension)

        assert_that(result, equal_to(True))
