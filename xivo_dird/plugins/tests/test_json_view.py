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
from hamcrest import has_entries
from hamcrest import is_in
from mock import ANY
from mock import Mock
from mock import patch
from mock import sentinel
from xivo_dird import make_result_class
from xivo_dird.plugins.default_json_view import DisplayAwareResult
from xivo_dird.plugins.default_json_view import DisplayColumn
from xivo_dird.plugins.default_json_view import JsonViewPlugin
from xivo_dird.plugins.default_json_view import _lookup


class TestJsonViewPlugin(unittest.TestCase):

    def setUp(self):
        self.http_app = flask.Flask(__name__)
        self.plugin = JsonViewPlugin()

    def test_parse_args(self):
        http_app = Mock()
        self.plugin.load({'http_app': http_app,
                          'services': {'lookup': sentinel.lookup_service},
                          'config': {'displays': {'display_1': sentinel.display_1,
                                                  'display_2': sentinel.display_2},
                                     'profile_to_display': {'profile_1': 'display_1',
                                                            'profile_2': 'display_2',
                                                            'profile_3': 'display_1'}}})

        assert_that(self.plugin.http_app, equal_to(http_app))
        assert_that(self.plugin.lookup_service, equal_to(sentinel.lookup_service))
        assert_that(self.plugin.displays, equal_to({
            'profile_1': sentinel.display_1,
            'profile_2': sentinel.display_2,
            'profile_3': sentinel.display_1,
        }))

    def test_default_view_load_no_args(self):
        self.plugin.load()

    def test_default_view_load_no_config(self):
        self.plugin.load({'http_app': Mock()})

    def test_default_view_load_no_displays(self):
        self.plugin.load({'http_app': Mock()})

    def test_default_view_load_no_lookup_service(self):
        self.plugin.load({'http_app': Mock()})

    def test_that_load_adds_the_route(self):
        args = {
            'http_app': self.http_app,
            'config': {'displays': {},
                       'profile_to_display': {}},
            'services': {'lookup': Mock()},
        }

        self.plugin.load(args)

        route = '/{version}/directories/lookup/<profile>'.format(version=JsonViewPlugin.API_VERSION)
        self.assert_has_route(self.http_app, route)

    def test_get_display_dict(self):
        args = {'displays': {'first_display': sentinel.display_1,
                             'second_display': sentinel.display_2},
                'profile_to_display': {'profile_1': 'first_display',
                                       'profile_2': 'second_display',
                                       'profile_3': 'first_display'}}
        self.plugin.load(args)

        display_dict = self.plugin._get_display_dict(args)

        expected = {
            'profile_1': sentinel.display_1,
            'profile_2': sentinel.display_2,
            'profile_3': sentinel.display_1,
        }

        assert_that(display_dict, equal_to(expected))

    @patch('xivo_dird.plugins.default_json_view.request', Mock(args={'term': [sentinel.term],
                                                                     'user_id': 42}))
    @patch('xivo_dird.plugins.default_json_view.make_response', Mock())
    @patch('xivo_dird.plugins.default_json_view.json', Mock())
    @patch('xivo_dird.plugins.default_json_view._lookup')
    def test_that_lookup_wrapper_calls_lookup(self, lookup):
        lookup.return_value([])
        self.plugin.lookup_service = Mock()
        profile = 'test'
        self.plugin.displays = {profile: sentinel.display}

        self.plugin._lookup_wrapper(profile)

        lookup.assert_called_once_with(self.plugin.lookup_service,
                                       sentinel.display,
                                       sentinel.term,
                                       profile,
                                       {'user_id': 42})

    @patch('xivo_dird.plugins.default_json_view.request', Mock(args={'user_id': 42}))
    @patch('xivo_dird.plugins.default_json_view.make_response')
    @patch('xivo_dird.plugins.default_json_view.json', Mock())
    @patch('xivo_dird.plugins.default_json_view._lookup', Mock())
    def test_that_lookup_wrapper_no_term_returns_400(self, make_response):
        result = self.plugin._lookup_wrapper(sentinel.profile)

        make_response.assert_called_once_with(ANY, 400)
        assert_that(result, equal_to(make_response.return_value))

    def assert_has_route(self, http_app, route):
        routes = self._list_routes(http_app)
        assert_that(route, is_in(routes))

    def _list_routes(self, http_app):
        return (rule.rule for rule in http_app.url_map.iter_rules())


class TestLookup(unittest.TestCase):

    def setUp(self):
        self.service = Mock()

    def test_that_lookup_forwards_term_to_the_service(self):
        self.service.return_value = []
        _lookup(self.service, [], sentinel.term, sentinel.profile, sentinel.args)

        self.service.assert_called_once_with(sentinel.term, sentinel.profile, sentinel.args)

    def test_that_lookup_adds_the_term_to_its_result(self):
        self.service.return_value = []

        result = _lookup(self.service, [], sentinel.term,
                         sentinel.profile, sentinel.args)

        assert_that(result, has_entries('term', sentinel.term))

    def test_that_lookup_adds_columns_headers(self):
        self.service.return_value = []
        display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, '', 'lastname'),
            DisplayColumn(None, 'status', None, None),
            DisplayColumn('Number', 'office_number', None, 'telephoneNumber'),
            DisplayColumn('Country', None, 'Canada', 'country'),
        ]

        result = _lookup(self.service, display, sentinel.term,
                         sentinel.profile, sentinel.args)

        expected_headers = ['Firstname', 'Lastname', None, 'Number', 'Country']
        assert_that(result, has_entries('column_headers', expected_headers))

    def test_that_lookup_adds_columns_types(self):
        self.service.return_value = []
        display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, '', 'lastname'),
            DisplayColumn(None, 'status', None, None),
            DisplayColumn('Number', 'office_number', None, 'telephoneNumber'),
            DisplayColumn('Country', None, 'Canada', 'country'),
        ]

        result = _lookup(self.service, display, sentinel.term,
                         sentinel.profile, sentinel.args)

        expected_types = [None, None, 'status', 'office_number', None]
        assert_that(result, has_entries('column_types', expected_types))

    def test_that_lookup_adds_results(self):
        self.service.return_value = r1, r2 = Mock(DisplayAwareResult), Mock(DisplayAwareResult)

        result = _lookup(self.service, {}, sentinel.term,
                         sentinel.profile, sentinel.args)

        assert_that(result, has_entries('results', [r1.to_dict.return_value,
                                                    r2.to_dict.return_value]))


class TestDisplayAwareResult(unittest.TestCase):

    def setUp(self):
        self.source_name = 'my_source'
        self.xivo_id = 'my_xivo_abc'
        self.SourceResult = make_result_class(self.source_name)

    def test_to_dict_no_relations(self):
        result = self.SourceResult({'firstname': 'Alice',
                                    'lastname': 'AAA',
                                    'telephoneNumber': '5555555555'})

        display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, '', 'lastname'),
            DisplayColumn(None, 'status', None, None),
            DisplayColumn('Number', 'office_number', None, 'telephoneNumber'),
            DisplayColumn('Country', None, 'Canada', 'country'),
        ]

        source = DisplayAwareResult(display, result)

        expected = {
            'column_values': ['Alice', 'AAA', None, '5555555555', 'Canada'],
            'relations': {'agent': None, 'user': None, 'endpoint': None},
            'source': self.source_name,
        }

        assert_that(source.to_dict(), equal_to(expected))

    def test_to_dict_with_relations(self):
        result = self.SourceResult({'firstname': 'Alice',
                                    'lastname': 'AAA',
                                    'telephoneNumber': '5555555555'},
                                   self.xivo_id, 'agent_id', 'user_id', 'endpoint_id')

        display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, '', 'lastname'),
            DisplayColumn(None, 'status', None, None),
            DisplayColumn('Number', 'office_number', None, 'telephoneNumber'),
            DisplayColumn('Country', None, 'Canada', 'country'),
        ]

        source = DisplayAwareResult(display, result)

        expected = {
            'column_values': ['Alice', 'AAA', None, '5555555555', 'Canada'],
            'relations': {'agent': {'id': 'agent_id',
                                    'xivo_id': self.xivo_id},
                          'user': {'id': 'user_id',
                                   'xivo_id': self.xivo_id},
                          'endpoint': {'id': 'endpoint_id',
                                       'xivo_id': self.xivo_id}},
            'source': self.source_name,
        }

        assert_that(source.to_dict(), equal_to(expected))
