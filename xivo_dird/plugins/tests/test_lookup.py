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
from flask import Flask
from flask_restplus.api import Api
from hamcrest import assert_that
from hamcrest import contains_inanyorder
from hamcrest import is_
from mock import Mock
from mock import patch
from mock import sentinel
from xivo_dird.plugins.lookup import API_VERSION
from xivo_dird.plugins.lookup import LookupServicePlugin
from xivo_dird.plugins.lookup import _LookupService
from xivo_dird.plugins.lookup import _SourceManager


class TestLookupServicePlugin(unittest.TestCase):

    def setUp(self):
        self._http_app = Flask(__name__)
        self._api = Api(self._http_app,
                        version='{}'.format(API_VERSION),
                        prefix='/{}'.format(API_VERSION))
        self._namespace = self._api.namespace('directories', description='XiVO directory services')
        self._args = {'config': {},
                      'http_app': self._http_app,
                      'api_namespace': self._namespace,
                      'rest_api': self._api}

    def test_instantiation(self):
        LookupServicePlugin()

    def test_load_no_http_app(self):
        p = LookupServicePlugin()
        args = copy(self._args)
        args.pop('http_app')

        self.assertRaises(ValueError, p.load)

    def test_load_no_api_namespace(self):
        p = LookupServicePlugin()
        args = copy(self._args)
        args.pop('api_namespace')

        self.assertRaises(ValueError, p.load, args)

    def test_load_no_rest_api(self):
        p = LookupServicePlugin()
        args = copy(self._args)
        args.pop('rest_api')

        self.assertRaises(ValueError, p.load, args)

    def test_load_no_config(self):
        p = LookupServicePlugin()
        args = copy(self._args)
        args.pop('config')

        self.assertRaises(ValueError, p.load, args)

    def test_that_load_setup_the_http_app(self):
        p = LookupServicePlugin()
        setup_http_app = p._setup_http_app = Mock()

        p.load(self._args)

        setup_http_app.assert_called_once_with(self._http_app, self._namespace, self._api)

    def test_that_load_instanciate_the_service_with_a_config(self):
        p = LookupServicePlugin()

        p.load(self._args)


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

        results = list(s.lookup(sentinel.term, sentinel.profile, sentinel.user_id))

        expected_results = self._result_1 + self._result_2

        print results, expected_results
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
