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

import unittest

from hamcrest import assert_that, equal_to, is_
from mock import ANY, patch, Mock

from xivo_dird.core.source_manager import SourceManager


class TestSourceManager(unittest.TestCase):

    @patch('stevedore.enabled.EnabledExtensionManager')
    def test_load_sources(self, extension_manager_init):
        extension_manager = extension_manager_init.return_value
        config = {
            'source_plugins': [
                'ldap',
                'xivo_phonebook',
            ],
        }

        manager = SourceManager(config)

        manager.load_sources()

        extension_manager_init.assert_called_once_with(
            namespace='xivo_dird.backends',
            check_func=manager.should_load_backend,
            invoke_on_load=False)
        extension_manager.map.assert_called_once_with(ANY, ANY)

    def test_should_load_backend(self):
        config = {
            'source_plugins': [
                'ldap',
            ]
        }
        backend_1 = Mock()
        backend_1.name = 'ldap'
        backend_2 = Mock()
        backend_2.name = 'xivo_phonebook'

        manager = SourceManager(config)

        assert_that(manager.should_load_backend(backend_1), is_(True))
        assert_that(manager.should_load_backend(backend_2), is_(False))

    def test_should_load_backend_missing_configs(self):
        backend_1 = Mock()
        backend_1.name = 'ldap'
        backend_2 = Mock()
        backend_2.name = 'xivo_phonebook'

        manager = SourceManager({})

        assert_that(manager.should_load_backend(backend_1), is_(False))
        assert_that(manager.should_load_backend(backend_2), is_(False))

    @patch('xivo_dird.core.source_manager._list_files')
    @patch('xivo_dird.core.source_manager._load_yaml_content')
    def test_load_all_configs(self, mock_load_yaml_content, mock_list_files):
        mock_list_files.return_value = files = ['file1']

        manager = SourceManager({'plugin_config_dir': 'foo'})

        manager._load_all_configs()

        mock_load_yaml_content.assert_called_once_with(files[0])

    def test_load_sources_using_backend_calls_load_on_all_sources_using_this_backend(self):
        configs = config1, config2 = [
            {
                'type': 'backend',
                'name': 'source1'
            },
            {
                'type': 'backend',
                'name': 'source2'
            }
        ]
        configs_by_backend = {
            'backend': configs
        }
        extension = Mock()
        extension.name = 'backend'
        source1, source2 = extension.plugin.side_effect = Mock(), Mock()
        manager = SourceManager({})

        manager._load_sources_using_backend(extension, configs_by_backend)

        assert_that(source1.name, equal_to('source1'))
        source1.load.assert_called_once_with(config1)
        assert_that(source2.name, equal_to('source2'))
        source2.load.assert_called_once_with(config2)
