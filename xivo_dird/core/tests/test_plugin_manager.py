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

        plugin_manager.load_services(s.config, rest_api)

        extension_manager_init.assert_called_once_with(
            namespace='xivo-dird.services',
            check_fun=ANY,
            invoke_on_load=True,
            invoke_args=[{
                'http_app': rest_api.app,
                'http_namespace': rest_api.namespace,
                'http_api': rest_api.api,
                'config': s.config
            }])
