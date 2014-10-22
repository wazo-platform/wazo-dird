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
from xivo_dird.plugins.default_json_view import DisplayColumn
from xivo_dird.plugins.default_json_view import JsonViewPlugin
from xivo_dird.plugins.default_json_view import _lookup
from xivo_dird.plugins.default_json_view import _lookup_wrapper


class TestJsonViewPlugin(unittest.TestCase):

    def setUp(self):
        self.http_app = flask.Flask(__name__)

    def test_default_view_load_no_args(self):
        p = JsonViewPlugin()

        p.load()

    def test_default_view_load_no_config(self):
        p = JsonViewPlugin()

        p.load({'http_app': Mock()})

    def test_that_load_adds_the_route(self):
        args = {
            'http_app': self.http_app,
            'config': {'displays': {}},
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
class TestLookupWrapper(unittest.TestCase):

    def setUp(self):
        self.lookup_service = Mock()
        self.services = {'lookup': self.lookup_service}
        self.view_config = {
            'displays': {
                'switchboard_display': [],
                'default_display': sentinel.default_display,
            },
            'profile_to_display': {
                'default': 'default_display',
                'switchboard': 'switchboard_display',
            },
        }

    @patch('xivo_dird.plugins.default_json_view.request', Mock(args={'term': sentinel.term,
                                                                     'user_id': sentinel.user_id}))
    @patch('xivo_dird.plugins.default_json_view._lookup')
    def test_that_lookup_wrapper_forwards_to_lookup(self, lookup, make_response):
        lookup.return_value = [{'a': 'result'}]

        result = _lookup_wrapper(self.services, self.view_config, 'default')

        lookup.assert_called_once_with(
            self.services['lookup'],
            self.view_config['displays']['default_display'],
            sentinel.term,
            'default',
            {'user_id': sentinel.user_id},
        )

        assert_that(result, equal_to(make_response.return_value))
        make_response.assert_called_once_with(json.dumps(lookup.return_value), 200)

    @patch('xivo_dird.plugins.default_json_view.request', Mock(args={}))
    @patch('xivo_dird.plugins.default_json_view.time')
    def test_that_lookup_with_no_term_return_a_400(self, mocked_time, mocked_make_response):
        mocked_time.return_value = t = '123455.343'
        results = _lookup_wrapper(self.services, {}, sentinel.profile)

        expected_json = json.dumps({'reason': ['term is missing'],
                                    'timestamp': [t],
                                    'status_code': 400})

        assert_that(results, equal_to(mocked_make_response.return_value))
        mocked_make_response.assert_called_once_with(expected_json, 400)

    @patch('xivo_dird.plugins.default_json_view.request', Mock(args={}))
    @patch('xivo_dird.plugins.default_json_view.time')
    def test_that_lookup_with_no_service_return_a_500(self, mocked_time, mocked_make_response):
        mocked_time.return_value = t = '123455.343'
        results = _lookup_wrapper({}, {}, sentinel.profile)

        expected_json = json.dumps({'reason': ['no lookup service available'],
                                    'timestamp': [t],
                                    'status_code': 500})

        assert_that(results, equal_to(mocked_make_response.return_value))
        mocked_make_response.assert_called_once_with(expected_json, 500)


class TestLookup(unittest.TestCase):

    def setUp(self):
        self.lookup_service = Mock()

    def test_that_lookup_forwards_term_to_the_service(self):
        self.lookup_service.return_value = []
        results = _lookup(self.lookup_service, sentinel.display,
                          sentinel.term, sentinel.profile, sentinel.args)

        assert_that(results, equal_to(self.lookup_service.return_value))
        self.lookup_service.assert_called_once_with(sentinel.term, sentinel.profile, sentinel.args)

    def test_that_lookup_renames_return_the_expected_columns_headers(self):
        display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, '', 'lastname'),
        ]

        self.lookup_service.return_value = [{'firstname': 'Alice', 'lastname': 'AAA'}]

        results = _lookup(self.lookup_service, display, sentinel.term,
                          sentinel.profile, sentinel.args)

        assert_that({'Firstname': 'Alice',
                     'Lastname': 'AAA'}, is_in(results))

    def test_that_lookup_removes_unwanted_columns(self):
        display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, '', 'lastname'),
        ]

        self.lookup_service.return_value = [{'firstname': 'Alice',
                                             'lastname': 'AAA',
                                             '__unique_id': ('1',)}]

        results = _lookup(self.lookup_service, display, sentinel.term,
                          sentinel.profile, sentinel.args)

        assert_that({'Firstname': 'Alice',
                     'Lastname': 'AAA'}, is_in(results))

    def test_that_lookup_adds_default_value_to_missing_columns(self):
        display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, '', 'lastname'),
            DisplayColumn('agent-id', None, 0, 'agent-id'),
        ]

        self.lookup_service.return_value = [{'firstname': 'Alice',
                                             'lastname': 'AAA'}]

        results = _lookup(self.lookup_service, display, sentinel.term,
                          sentinel.profile, sentinel.args)

        assert_that({'Firstname': 'Alice',
                     'Lastname': 'AAA',
                     'agent-id': 0}, is_in(results))
