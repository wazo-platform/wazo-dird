# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import unittest

from copy import copy
from hamcrest import assert_that
from hamcrest import contains_inanyorder
from hamcrest import is_
from mock import Mock
from mock import patch
from mock import sentinel
from xivo_dird.plugins.lookup import LookupServicePlugin
from xivo_dird.plugins.lookup import _LookupService
from xivo_dird.plugins.lookup import _SourceManager


class TestLookupServicePlugin(unittest.TestCase):

    def setUp(self):
        self._args = {'config': {}}

    def test_instantiation(self):
        LookupServicePlugin()

    def test_load_no_config(self):
        p = LookupServicePlugin()
        args = copy(self._args)
        args.pop('config')

        self.assertRaises(ValueError, p.load, args)


class TestLookupService(unittest.TestCase):

    def setUp(self):
        self._config = {}
        self._profile = 'my_profile'
        self._source_manager = Mock(_SourceManager)
        self._source_1 = Mock()
        self._source_2 = Mock()
        self._source_3 = Mock()
        self._columns_1 = ['firstname', 'lastname', 'number']
        self._columns_2 = ['firstname', 'lastname', 'number', 'email']
        self._source_manager.get_by_profile.return_value = [(self._source_1, self._columns_1),
                                                            (self._source_2, self._columns_2)]
        self._result_1 = [dict(zip(self._columns_1, ['Alice', 'AAA', '5555551234'])),
                          dict(zip(self._columns_1, ['Bob', 'BBB', '5555555678']))]
        self._result_2 = [dict(zip(self._columns_2, ['Charles', 'CCC', '1234', 'charles@example.org']))]
        self._source_1.search.return_value = self._result_1
        self._source_2.search.return_value = self._result_2

    def test_lookup(self):
        s = _LookupService(self._config)
        s._source_manager = self._source_manager
        args = {'user_id': sentinel.user_id}

        results = list(s.execute(sentinel.term, sentinel.profile, sentinel.user_id))

        expected_results = self._result_1 + self._result_2

        assert_that(results, contains_inanyorder(*expected_results))

        self._source_1.search.assert_called_once_with(sentinel.term, args, self._columns_1)
        self._source_2.search.assert_called_once_with(sentinel.term, args, self._columns_2)


class TestSourceManager(unittest.TestCase):

    @patch('stevedore.enabled.EnabledExtensionManager')
    def test_load_backends(self, mock_enabled_extension_manager):
        config = {
            'source_plugins': [
                'ldap',
                'xivo_phonebook',
            ],
        }

        s = _SourceManager(config)

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

        s = _SourceManager(config)

        assert_that(s.should_load_backend(backend_1), is_(True))
        assert_that(s.should_load_backend(backend_2), is_(False))

    def test_should_load_backend_missing_configs(self):
        backend_1 = Mock()
        backend_1.name = 'ldap'
        backend_2 = Mock()
        backend_2.name = 'xivo_phonebook'

        s = _SourceManager({})

        assert_that(s.should_load_backend(backend_1), is_(False))
        assert_that(s.should_load_backend(backend_2), is_(False))
