# Copyright 2014-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import unittest

from hamcrest import assert_that, equal_to, has_entries
from mock import (
    ANY,
    Mock,
    sentinel as s,
)

from wazo_dird.plugins.tests.base_http_view_test_case import BaseHTTPViewTestCase
from wazo_dird.helpers import DisplayColumn
from ..plugin import HeadersViewPlugin
from ..http import (
    Headers,
    format_headers,
)


class TestHeadersView(BaseHTTPViewTestCase):

    def setUp(self):
        super().setUp()
        self.api = Mock()

    def test_that_load_add_the_route(self):
        http_namespace = Mock()
        dependencies = {
            'http_namespace': http_namespace,
            'api': self.api,
            'config': {'views': {'profile_to_display': s.profile_to_display}},
            'services': {
                'display': s.display_service,
            },
        }

        HeadersViewPlugin().load(dependencies)

        self.api.add_resource.assert_called_once_with(
            ANY,
            '/directories/lookup/<profile>/headers',
            resource_class_args=(s.display_service, s.profile_to_display),
        )

    def test_result(self):
        display_service = Mock()
        display_service.list_.return_value = [
            {
                'name': 'display_2',
                'columns': [
                    {
                        'title': 'fn',
                        'type': 'some_type',
                        'default': 'N/A',
                        'field': 'firstname',
                    },
                    {
                        'title': 'ln',
                        'type': None,
                        'default': 'N/A',
                        'field': 'LAST',
                    },
                ],
            },
        ]

        profile_to_display = {
            'profile_1': 'display_1',
            'profile_2': 'display_2',
            'profile_3': 'display_1',
        }

        result = Headers(display_service, profile_to_display).get('profile_2')

        expected_result = {
            'column_headers': ['fn', 'ln'],
            'column_types': ['some_type', None],
        }
        assert_that(result, equal_to(expected_result))


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
