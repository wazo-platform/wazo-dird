# -*- coding: utf-8 -*-
# Copyright (C) 2014-2015 Avencall
# Copyright (C) 2016 Proformatique, Inc
# SPDX-License-Identifier: GPL-3.0+

import unittest

from hamcrest import assert_that, equal_to, has_entries
from mock import ANY, Mock, patch

from xivo_dird.plugins.views.tests.base_http_view_test_case import BaseHTTPViewTestCase
from ..headers_view import DisplayColumn, Headers, HeadersViewPlugin, format_headers, make_displays


class TestHeadersView(BaseHTTPViewTestCase):

    def tearDown(self):
        Headers.configure(displays=None)

    @patch('xivo_dird.plugins.views.headers.headers_view.api.add_resource')
    def test_that_load_add_the_route(self, add_resource):
        http_namespace = Mock()
        args = {'http_namespace': http_namespace,
                'rest_api': Mock(),
                'config': {}}

        HeadersViewPlugin().load(args)

        add_resource.assert_called_once_with(ANY, '/directories/lookup/<profile>/headers')

    def test_result(self):
        config = {'displays': {'display_1': [{'title': 'Firstname',
                                              'type': None,
                                              'default': 'Unknown',
                                              'field': 'firstname'},
                                             {'title': 'Lastname',
                                              'type': None,
                                              'default': 'ln',
                                              'field': 'lastname'}],
                               'display_2': [{'title': 'fn',
                                              'type': 'some_type',
                                              'default': 'N/A',
                                              'field': 'firstname'},
                                             {'title': 'ln',
                                              'type': None,
                                              'default': 'N/A',
                                              'field': 'LAST'}]},
                  'profile_to_display': {'profile_1': 'display_1',
                                         'profile_2': 'display_2',
                                         'profile_3': 'display_1'}}
        Headers.configure(displays=make_displays(config))

        result = Headers().get('profile_2')

        expected_result = {
            'column_headers': ['fn', 'ln'],
            'column_types': ['some_type', None],
        }
        assert_that(result, equal_to(expected_result))


class TestMakeDisplays(unittest.TestCase):

    def test_that_make_displays_with_no_config_returns_empty_dict(self):
        result = make_displays({})

        assert_that(result, equal_to({}))

    def test_that_make_displays_generate_display_dict(self):
        first_display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, 'ln', 'lastname'),
        ]
        second_display = [
            DisplayColumn('fn', 'some_type', 'N/A', 'firstname'),
            DisplayColumn('ln', None, 'N/A', 'LAST'),
        ]

        config = {'displays': {'first_display': [{'title': 'Firstname',
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
                                         'profile_3': 'first_display'}}

        display_dict = make_displays(config)

        expected = {
            'profile_1': first_display,
            'profile_2': second_display,
            'profile_3': first_display,
        }

        assert_that(display_dict, equal_to(expected))


class TestFormatHeaders(unittest.TestCase):

    def test_that_format_headers_adds_columns_headers(self):
        display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, '', 'lastname'),
            DisplayColumn(None, 'status', None, None),
            DisplayColumn('Number', 'office_number', None, 'telephoneNumber'),
            DisplayColumn('Country', None, 'Canada', 'country'),
        ]

        result = format_headers(display)

        expected_headers = ['Firstname', 'Lastname', None, 'Number', 'Country']
        assert_that(result, has_entries('column_headers', expected_headers))

    def test_that_format_headers_adds_columns_types(self):
        display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, '', 'lastname'),
            DisplayColumn(None, 'status', None, None),
            DisplayColumn('Number', 'office_number', None, 'telephoneNumber'),
            DisplayColumn('Country', None, 'Canada', 'country'),
        ]

        result = format_headers(display)

        expected_types = [None, None, 'status', 'office_number', None]
        assert_that(result, has_entries('column_types', expected_types))
