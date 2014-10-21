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

from hamcrest import assert_that, contains_inanyorder, is_
from mock import patch, Mock

from xivo_dird.core.source_manager import SourceManager


class TestSourceManager(unittest.TestCase):

    @patch('stevedore.enabled.EnabledExtensionManager')
    def test_load_backends(self, mock_enabled_extension_manager):
        config = {
            'source_plugins': [
                'ldap',
                'xivo_phonebook',
            ],
        }

        s = SourceManager(config)

        s.load_backends()

        mock_enabled_extension_manager.assert_called_once_with(
            namespace='xivo-dird.backends',
            check_func=s.should_load_backend,
            invoke_on_load=False)

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

        s = SourceManager(config)

        assert_that(s.should_load_backend(backend_1), is_(True))
        assert_that(s.should_load_backend(backend_2), is_(False))

    def test_should_load_backend_missing_configs(self):
        backend_1 = Mock()
        backend_1.name = 'ldap'
        backend_2 = Mock()
        backend_2.name = 'xivo_phonebook'

        s = SourceManager({})

        assert_that(s.should_load_backend(backend_1), is_(False))
        assert_that(s.should_load_backend(backend_2), is_(False))

    @patch('xivo_dird.core.source_manager._list_files')
    @patch('xivo_dird.core.source_manager._load_yaml_content')
    def test_load_all_configs(self, mock_load_yaml_content, mock_list_files):
        mock_list_files.return_value = files = ['file1']

        s = SourceManager({'plugin_config_dir': 'foo'})

        s._load_all_configs()

        mock_load_yaml_content.assert_called_once_with(files[0])
