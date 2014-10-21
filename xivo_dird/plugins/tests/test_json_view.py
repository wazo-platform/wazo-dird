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

import flask
import json
import unittest

from hamcrest import assert_that
from hamcrest import equal_to
from hamcrest import is_in
from mock import Mock
from mock import patch
from mock import sentinel
from xivo_dird.plugins.default_json_view import JsonViewPlugin
from xivo_dird.plugins.default_json_view import _lookup_wrapper


class TestJsonViewPlugin(unittest.TestCase):

    def setUp(self):
        self.http_app = flask.Flask(__name__)

    def test_default_view_load_no_args(self):
        p = JsonViewPlugin()

        p.load()

    def test_that_load_adds_the_route(self):
        args = {
            'http_app': self.http_app,
        }

        p = JsonViewPlugin()
        p.load(args)

        route = '/{version}/directories/lookup/<profile>'.format(version=JsonViewPlugin.API_VERSION)
        self.assert_has_route(self.http_app, route)

    def assert_has_route(self, http_app, route):
        routes = self._list_routes(http_app)
        assert_that(route, is_in(routes))

    def _list_routes(self, http_app):
        return (rule.rule for rule in http_app.url_map.iter_rules())


@patch('xivo_dird.plugins.default_json_view.make_response')
class TestLookup(unittest.TestCase):

    def setUp(self):
        self.lookup_service = Mock()
        self.services = {'lookup': self.lookup_service}

    @patch('xivo_dird.plugins.default_json_view.request', Mock(args={'term': sentinel.term}))
    def test_that_lookup_forwards_the_profile_and_term_to_the_service(self, mocked_make_response):
        self.lookup_service.return_value = [{'a': 'result'}]
        result = _lookup_wrapper(self.services, sentinel.profile)

        self.lookup_service.assert_called_once_with(sentinel.term, sentinel.profile, {})

        assert_that(result, equal_to(mocked_make_response.return_value))
        mocked_make_response.assert_called_once_with(
            json.dumps(self.lookup_service.return_value), 200)

    @patch('xivo_dird.plugins.default_json_view.request',
           Mock(args={'term': sentinel.term, 'user_id': sentinel.user_id}))
    def test_that_lookup_forwards_extra_args_to_the_service(self, mocked_make_response):
        self.lookup_service.return_value = [{'a': 'result'}]
        result = _lookup_wrapper(self.services, sentinel.profile)

        self.lookup_service.assert_called_once_with(sentinel.term, sentinel.profile,
                                                    {'user_id': sentinel.user_id})

        assert_that(result, equal_to(mocked_make_response.return_value))
        mocked_make_response.assert_called_once_with(
            json.dumps(self.lookup_service.return_value), 200)

    @patch('xivo_dird.plugins.default_json_view.request', Mock(args={}))
    @patch('xivo_dird.plugins.default_json_view.time')
    def test_that_lookup_with_no_term_return_a_400(self, mocked_time, mocked_make_response):
        mocked_time.return_value = t = '123455.343'
        results = _lookup_wrapper(self.services, sentinel.profile)

        expected_json = json.dumps({'reason': ['term is missing'],
                                    'timestamp': [t],
                                    'status_code': 400})

        assert_that(results, equal_to(mocked_make_response.return_value))
        mocked_make_response.assert_called_once_with(expected_json, 400)

    @patch('xivo_dird.plugins.default_json_view.request', Mock(args={'term': sentinel.term}))
    def test_that_lookup_with_no_service_return_an_empty_result(self, mocked_make_response):
        results = _lookup_wrapper({}, sentinel.profile)

        assert_that(results, equal_to(mocked_make_response.return_value))
        mocked_make_response.assert_called_once_with(json.dumps([]), 200)
