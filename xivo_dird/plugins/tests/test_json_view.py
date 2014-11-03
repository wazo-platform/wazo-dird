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
import unittest

from hamcrest import assert_that
from hamcrest import equal_to
from hamcrest import has_entries
from hamcrest import is_not
from mock import Mock
from mock import patch
from mock import sentinel
from xivo_dird import make_result_class
from xivo_dird.plugins.default_json_view import DisplayAwareResult
from xivo_dird.plugins.default_json_view import DisplayColumn
from xivo_dird.plugins.default_json_view import JsonViewPlugin
from xivo_dird.plugins.default_json_view import _lookup
from xivo_dird.plugins.tests.base_http_view_test_case import BaseHTTPViewTestCase


class TestJsonViewPlugin(BaseHTTPViewTestCase):

    def setUp(self):
        self.http_app = flask.Flask(__name__)
        self.plugin = JsonViewPlugin()

    def test_default_view_load_no_lookup_service(self):
        self.plugin.load({'http_app': Mock(),
                          'services': {}})

        route = '/{version}/directories/lookup/<profile>'.format(version=JsonViewPlugin.API_VERSION)
        assert_that(route, is_not(self.is_route_of_app(self.http_app)))

    def test_that_load_adds_the_route(self):
        args = {
            'http_app': self.http_app,
            'config': {'displays': {},
                       'profile_to_display': {}},
            'services': {'lookup': Mock()},
        }

        self.plugin.load(args)

        route = '/{version}/directories/lookup/<profile>'.format(version=JsonViewPlugin.API_VERSION)
        assert_that(route, self.is_route_of_app(self.http_app))

    def test_get_display_dict(self):
        first_display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, 'ln', 'lastname'),
        ]
        second_display = [
            DisplayColumn('fn', 'some_type', 'N/A', 'firstname'),
            DisplayColumn('ln', None, 'N/A', 'LAST'),
        ]

        args = {'config': {'displays': {'first_display': [{'title': 'Firstname',
                                                           'type': None,
                                                           'default': 'Unknown',
                                                           'field': 'firstname'},
                                                          {'title': 'Lastname',
                                                           'type': None,
                                                           'default': 'ln',
                                                           'field': 'lastname'}],
                                        'second_display': [{'title': 'fn',
                                                            'type': 'some_type',
                                                            'default': 'N/A',
                                                            'field': 'firstname'},
                                                           {'title': 'ln',
                                                            'type': None,
                                                            'default': 'N/A',
                                                            'field': 'LAST'}]},
                           'profile_to_display': {'profile_1': 'first_display',
                                                  'profile_2': 'second_display',
                                                  'profile_3': 'first_display'}},
                'services': {'lookup': Mock()},
                'http_app': Mock()}
        self.plugin.load(args)

        display_dict = self.plugin._get_display_dict(args['config'])

        expected = {
            'profile_1': first_display,
            'profile_2': second_display,
            'profile_3': first_display,
        }

        assert_that(display_dict, equal_to(expected))

    @patch('xivo_dird.plugins.default_json_view.request', Mock(args={'term': [sentinel.term],
                                                                     'user_id': 42}))
    @patch('xivo_dird.plugins.default_json_view.jsonify', Mock())
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
    @patch('xivo_dird.plugins.default_json_view.jsonify')
    @patch('xivo_dird.plugins.default_json_view._lookup', Mock())
    def test_that_lookup_wrapper_no_term_returns_400(self, jsonify):
        result = self.plugin._lookup_wrapper(sentinel.profile)

        assert_that(result[0], equal_to(jsonify.return_value))
        assert_that(result[1], equal_to(400))


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

    @patch('xivo_dird.plugins.default_json_view.DisplayAwareResult')
    def test_that_lookup_adds_results(self, MockedDisplayAwareResult):
        self.service.return_value = r1, r2 = Mock(), Mock()
        display = []

        result = _lookup(self.service, display, sentinel.term,
                         sentinel.profile, sentinel.args)

        assert_that(result, has_entries('results', [
            MockedDisplayAwareResult(display, r1).to_dict.return_value,
            MockedDisplayAwareResult(display, r2).to_dict.return_value]))


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
