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

from hamcrest import assert_that
from hamcrest import equal_to
from mock import ANY
from mock import Mock
from mock import patch
from xivo_dird.plugins.headers_view import HeadersViewPlugin
from xivo_dird.plugins.headers_view import make_api_class
from xivo_dird.plugins.tests.base_http_view_test_case import BaseHTTPViewTestCase


class TestHeadersView(BaseHTTPViewTestCase):

    def test_that_load_add_the_route(self):
        http_namespace = Mock()
        args = {'http_namespace': http_namespace,
                'rest_api': Mock(),
                'config': {}}

        HeadersViewPlugin().load(args)

        http_namespace.route.assert_called_once_with('/lookup/<profile>/headers', doc=ANY)

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
        api_class = make_api_class(config, namespace=Mock(), api=Mock())

        result = api_class().get('profile_2')

        expected_result = {
            'column_headers': ['fn', 'ln'],
            'column_types': ['some_type', None],
        }
        assert_that(result, equal_to(expected_result))

    @patch('xivo_dird.plugins.headers_view.time', Mock(return_value='now'))
    def test_result_with_a_bad_profile(self):
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
        api_class = make_api_class(config, namespace=Mock(), api=Mock())

        result, code = api_class().get('profile_XXX')

        expected_result = {
            'reason': ['The lookup profile does not exist'],
            'timestamp': ['now'],
            'status_code': 404,
        }
        assert_that(result, equal_to(expected_result))
        assert_that(code, equal_to(404))
