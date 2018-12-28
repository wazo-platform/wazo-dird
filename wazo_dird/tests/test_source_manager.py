# Copyright 2014-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import unittest

from collections import (
    defaultdict,
    OrderedDict,
)
from hamcrest import assert_that, equal_to, contains
from mock import ANY, patch, Mock, sentinel as s

from wazo_dird.source_manager import SourceManager


class TestSourceManager(unittest.TestCase):

    @patch('wazo_dird.source_manager.NamedExtensionManager')
    def test_that_load_sources_loads_the_enabled_and_configured_sources(self, extension_manager_init):
        extension_manager = extension_manager_init.return_value
        enabled_backends = OrderedDict([
            ('ldap', True),
            ('xivo_phonebook', True),
        ])
        my_ldap_config = {'type': 'ldap',
                          'name': 'my_ldap'}
        sources_by_type = defaultdict(list)
        sources_by_type['ldap'].append(my_ldap_config)

        manager = SourceManager(
            enabled_backends,
            {'sources': {'my_ldap': my_ldap_config}},
            s.auth_client,
            s.token_renewer,
            s.rest_api,
        )

        manager.load_sources()

        extension_manager_init.assert_called_once_with(
            'wazo_dird.backends',
            ['ldap', 'xivo_phonebook'],
            name_order=True,
            on_load_failure_callback=ANY,
            invoke_on_load=True,
            on_missing_entrypoints_callback=ANY,
        )
        extension_manager.map.assert_called_once_with(ANY, sources_by_type)

    @patch('wazo_dird.source_manager.NamedExtensionManager')
    def test_load_sources_returns_dict_of_sources(self, extension_manager_init):
        enabled_backends = {
            'ldap': True,
            'xivo_phonebook': True,
        }

        manager = SourceManager(
            enabled_backends,
            {'sources': {}},
            s.auth_client,
            s.token_renewer,
            s.rest_api,
        )
        manager._sources = s.sources

        result = manager.load_sources()

        assert_that(result, equal_to(s.sources))

    def test_load_sources_using_backend_calls_load_on_all_sources_using_this_backend(self):
        config1 = {'type': 'backend', 'name': 'source1'}
        config2 = {'type': 'backend', 'name': 'source2'}
        main_config = {'sources': {'source1': config1, 'source2': config2}}
        configs_by_backend = {'backend': [config1, config2]}
        extension = Mock()
        extension.name = 'backend'
        source1, source2 = extension.plugin.side_effect = Mock(), Mock()

        manager = SourceManager([], main_config, s.auth_client, s.token_renewer, s.rest_api)

        manager._load_sources_using_backend(extension, configs_by_backend)

        assert_that(source1.name, equal_to('source1'))
        source1.load.assert_called_once_with(
            {
                'config': config1,
                'main_config': main_config,
                'auth_client': s.auth_client,
                'token_renewer': s.token_renewer,
                'rest_api': s.rest_api,
            },
        )
        source2.load.assert_called_once_with(
            {
                'config': config2,
                'main_config': main_config,
                'auth_client': s.auth_client,
                'token_renewer': s.token_renewer,
                'rest_api': s.rest_api,
            },
        )

    def test_load_sources_using_backend_calls_load_on_all_sources_with_exceptions(self):
        config1 = {'type': 'backend', 'name': 'source1'}
        config2 = {'type': 'backend', 'name': 'source2'}
        main_config = {'sources': {'source1': config1, 'source2': config2}}
        configs_by_backend = {'backend': [config1, config2]}
        extension = Mock()
        extension.name = 'backend'
        source1, source2 = extension.plugin.side_effect = Mock(), Mock()
        source1.load.side_effect = RuntimeError
        manager = SourceManager([], main_config, s.auth_client, s.token_renewer, s.rest_api)

        manager._load_sources_using_backend(extension, configs_by_backend)

        assert_that(list(manager._sources.keys()), contains('source2'))
        assert_that(source2.name, equal_to('source2'))
        source2.load.assert_called_once_with(
            {
                'config': config2,
                'main_config': main_config,
                'auth_client': s.auth_client,
                'token_renewer': s.token_renewer,
                'rest_api': s.rest_api,
            },
        )

    def test_unload_sources(self):
        source_1 = Mock()
        source_2 = Mock()

        manager = SourceManager([], {'sources': {}}, s.auth_client, s.token_renewer, s.rest_api)
        manager._sources = {'s1': source_1, 's2': source_2}

        manager.unload_sources()

        source_1.unload.assert_called_once_with()
        source_2.unload.assert_called_once_with()
