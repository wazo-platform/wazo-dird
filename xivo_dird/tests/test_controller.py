# -*- coding: utf-8 -*-

# Copyright (C) 2014-2016 Avencall
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


from mock import ANY, Mock, patch, sentinel as s
from unittest import TestCase

from xivo_dird.controller import Controller


class TestController(TestCase):

    def setUp(self):
        self.rest_api = patch('xivo_dird.controller.CoreRestApi').start().return_value
        self.load_services = patch('xivo_dird.core.plugin_manager.load_services').start()
        self.unload_services = patch('xivo_dird.core.plugin_manager.unload_services').start()
        self.load_sources = patch('xivo_dird.core.plugin_manager.load_sources').start()
        self.load_views = patch('xivo_dird.core.plugin_manager.load_views').start()

    def tearDown(self):
        patch.stopall()

    def test_run_starts_rest_api(self):
        config = self._create_config(**{
            'rest_api': {'https': {'listen': '127.0.0.1', 'port': '9489', 'certificate': 'my-certificate'}},
            'debug': s.debug,
            'service_discovery': {'enabled': False},
        })
        Controller(config).run()

        self.rest_api.run.assert_called_once_with()

    def test_run_loads_services(self):
        config = self._create_config(**{
            'enabled_plugins': {
                'services': s.enabled,
            },
            'services': s.config,
            'service_discovery': {'enabled': False},
        })

        Controller(config).run()

        self.load_services.assert_called_once_with(config, s.enabled, ANY)

    def test_del_unloads_services(self):
        config = self._create_config()
        controller = Controller(config)

        del(controller)

        self.unload_services.assert_called_once_with()

    def test_run_loads_sources(self):
        config = self._create_config(**{
            'enabled_plugins': {
                'backends': s.enabled,
                'services': []
            },
            'sources': s.source_configs,
            'service_discovery': {'enabled': False},
        })

        Controller(config).run()

        self.load_sources.assert_called_once_with(s.enabled, config)

    def test_run_loads_views(self):
        config = self._create_config(**{
            'enabled_plugins': {
                'views': s.enabled,
            },
            'views': s.config,
            'service_discovery': {'enabled': False},
        })

        Controller(config).run()

        self.load_views.assert_called_once_with(s.config, s.enabled, ANY, self.rest_api)

    def _create_config(self, **kwargs):
        config = dict(kwargs)
        config.setdefault('auth', {})
        config.setdefault('enabled_plugins', {})
        config['enabled_plugins'].setdefault('backends', [])
        config['enabled_plugins'].setdefault('services', [])
        config['enabled_plugins'].setdefault('views', [])
        config.setdefault('sources', {})
        config.setdefault('rest_api', {'https': {'port': Mock(), 'certificate': 'my-certificate'}})
        config.setdefault('services', Mock())
        config.setdefault('source_config_dir', Mock())
        config.setdefault('views', Mock())
        return config
