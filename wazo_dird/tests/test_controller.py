# Copyright 2014-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase

from mock import ANY, Mock, patch, sentinel as s

from wazo_dird.controller import Controller

token_renewer = Mock()
token_renewer.__enter__ = Mock()
token_renewer.__exit__ = Mock()
TokenRenewer = Mock(return_value=token_renewer)
CoreBus = Mock(
    return_value=Mock(
        __enter__=Mock(),
        __exit__=Mock(),
    )
)


@patch('wazo_dird.controller.TokenRenewer', TokenRenewer)
@patch('wazo_dird.controller.CoreBus', CoreBus)
@patch('wazo_dird.controller.init_db', Mock())
class TestController(TestCase):
    def setUp(self):
        self.rest_api = patch('wazo_dird.controller.CoreRestApi').start().return_value
        self.load_services = patch('wazo_dird.plugin_manager.load_services').start()
        self.unload_services = patch('wazo_dird.plugin_manager.unload_services').start()
        self.load_views = patch('wazo_dird.plugin_manager.load_views').start()

    def tearDown(self):
        patch.stopall()

    def test_run_starts_rest_api(self):
        config = self._create_config(
            **{
                'rest_api': {
                    'listen': '127.0.0.1',
                    'port': '9489',
                    'certificate': 'my-certificate',
                },
                'debug': s.debug,
                'service_discovery': {'enabled': False},
            }
        )
        Controller(config).run()

        self.rest_api.run.assert_called_once_with()

    def test_run_loads_and_unloads_services(self):
        config = self._create_config(
            **{
                'enabled_plugins': {'services': s.enabled},
                'services': s.config,
                'service_discovery': {'enabled': False},
            }
        )

        Controller(config).run()

        self.load_services.assert_called_once_with(config, s.enabled, ANY, ANY, ANY)
        self.unload_services.assert_called_once_with()

    def test_run_loads_views(self):
        config = self._create_config(
            **{
                'enabled_plugins': {'views': s.enabled},
                'views': s.config,
                'service_discovery': {'enabled': False},
            }
        )

        controller = Controller(config)
        controller.run()

        self.load_views.assert_called_once_with(
            config,
            s.enabled,
            ANY,
            controller.auth_client,
            controller.status_aggregator,
            controller.rest_api,
        )

    def _create_config(self, **kwargs):
        config = dict(kwargs)
        config.setdefault('bus', {'enabled': False})
        config.setdefault('auth', {'host': 'localhost'})
        config.setdefault('enabled_plugins', {})
        config['enabled_plugins'].setdefault('backends', {})
        config['enabled_plugins'].setdefault('services', {})
        config['enabled_plugins'].setdefault('views', {})
        config.setdefault('sources', {})
        config.setdefault('rest_api', {'port': Mock(), 'certificate': 'my-certificate'})
        config.setdefault('services', Mock())
        config.setdefault('source_config_dir', Mock())
        config.setdefault('views', Mock())
        config.setdefault('db_uri', s.db_uri)
        return config
