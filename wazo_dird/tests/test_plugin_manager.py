# Copyright 2014-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase

from hamcrest import assert_that, calling, equal_to, raises, not_
from mock import Mock, patch, sentinel as s

from wazo_dird import plugin_manager


class TestPluginManagerServices(TestCase):

    def test_unload_services_calls_unload_on_services(self):
        plugin_manager.services_extension_manager = Mock()

        plugin_manager.unload_services()

        plugin_manager.services_extension_manager.map_method.assert_called_once_with('unload')

    def test_that_unload_services_does_nothing_when_load_services_has_not_been_run(self):
        with patch('wazo_dird.plugin_manager.services_extension_manager', None):
            assert_that(calling(plugin_manager.unload_services),
                        not_(raises(Exception)))


class TestPluginManagerSources(TestCase):

    def tearDown(self):
        plugin_manager.source_manager = None

    @patch('wazo_dird.plugin_manager.SourceManager')
    def test_load_sources_calls_source_manager(self, source_manager_init):
        source_manager = source_manager_init.return_value

        plugin_manager.load_sources(
            s.enabled,
            s.source_config_dir,
            s.auth_client,
            s.token_renewer,
            s.rest_api,
        )
        source_manager_init.assert_called_once_with(
            s.enabled,
            s.source_config_dir,
            s.auth_client,
            s.token_renewer,
            s.rest_api,
        )
        source_manager.load_sources.assert_called_once_with()

    @patch('wazo_dird.plugin_manager.SourceManager')
    def test_load_sources_returns_result_from_source_manager_load(self, source_manager_init):
        source_manager = source_manager_init.return_value
        source_manager.load_sources.return_value = s.result

        result = plugin_manager.load_sources(
            s.enabled,
            s.source_config_dir,
            s.auth_client,
            s.token_renewer,
            s.rest_api,
        )

        assert_that(result, equal_to(s.result))
