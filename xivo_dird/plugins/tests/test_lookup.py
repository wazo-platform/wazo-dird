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
from mock import Mock
from xivo_dird.plugins.lookup import API_VERSION
from xivo_dird.plugins.lookup import LookupServicePlugin as LookupService


class TestLookup(unittest.TestCase):

    def setUp(self):
        self._http_app = Flask(__name__)
        self._api = Api(self._http_app,
                        version='{}'.format(API_VERSION),
                        prefix='/{}'.format(API_VERSION))
        self._namespace = self._api.namespace('directories', description='XiVO directory services')
        self._args = {'http_app': self._http_app,
                      'api_namespace': self._namespace,
                      'rest_api': self._api}

    def test_instantiation(self):
        LookupService()

    def test_load_no_http_app(self):
        s = LookupService()
        args = copy(self._args)
        args.pop('http_app')

        self.assertRaises(ValueError, s.load)

    def test_load_no_api_namespace(self):
        s = LookupService()
        args = copy(self._args)
        args.pop('api_namespace')

        self.assertRaises(ValueError, s.load, args)

    def test_load_no_rest_api(self):
        s = LookupService()
        args = copy(self._args)
        args.pop('rest_api')

        self.assertRaises(ValueError, s.load, args)

    def test_that_load_setup_the_http_app(self):
        s = LookupService()
        setup_http_app = s._setup_http_app = Mock()

        s.load(self._args)

        setup_http_app.assert_called_once_with(self._http_app, self._namespace, self._api)
