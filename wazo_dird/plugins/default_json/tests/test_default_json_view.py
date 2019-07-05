# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from uuid import uuid4

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import has_entries
from hamcrest import has_entry
from hamcrest import has_item
from hamcrest import not_
from mock import (
    ANY,
    call,
    Mock,
    sentinel as s,
)

from wazo_dird.helpers import DisplayColumn
from wazo_dird import make_result_class
from wazo_dird.plugins.tests.base_http_view_test_case import BaseHTTPViewTestCase

from ..plugin import (
    JsonViewPlugin,
)
from ..http import (
    FavoritesRead,
    FavoritesWrite,
    Lookup,
    Personal,
    _ResultFormatter,
)

UUID1 = str(uuid4())
UUID2 = str(uuid4())


class TestJsonViewPlugin(BaseHTTPViewTestCase):

    def setUp(self):
        self.api = Mock()
        self.plugin = JsonViewPlugin()

    def test_that_load_with_no_lookup_service_does_not_add_route(self):
        self.plugin.load({'config': {},
                          'http_namespace': Mock(),
                          'api': self.api,
                          'services': {}})

        assert_that(
            self.api.add_resource.call_args_list,
            not_(has_item(call(Lookup, ANY))),
        )

    def test_that_load_adds_the_lookup_route(self):
        dependencies = {
            'http_namespace': Mock(),
            'api': self.api,
            'services': {
                'lookup': s.lookup_service,
                'display': s.display_service,
                'favorites': s.favorites_service,
                'profile': s.profile_service,
            },
        }

        self.plugin.load(dependencies)

        self.api.add_resource.assert_any_call(
            Lookup,
            JsonViewPlugin.lookup_url,
            resource_class_args=(
                s.lookup_service,
                s.favorites_service,
                s.display_service,
                s.profile_service,
            ),
        )

    def test_that_load_with_no_favorites_service_does_not_add_route(self):
        JsonViewPlugin().load({'config': {},
                               'http_namespace': Mock(),
                               'api': self.api,
                               'services': {}})

        assert_that(self.api.add_resource.call_args_list, not_(has_item(
            call(FavoritesRead, ANY),
        )))
        assert_that(self.api.add_resource.call_args_list, not_(has_item(
            call(FavoritesWrite, ANY),
        )))

    def test_that_load_adds_the_favorite_route(self):
        dependencies = {
            'http_namespace': Mock(),
            'api': self.api,
            'services': {
                'favorites': s.favorite_service,
                'display': s.display_service,
                'profile': s.profile_service,
            },
        }

        JsonViewPlugin().load(dependencies)

        self.api.add_resource.assert_any_call(
            FavoritesRead,
            JsonViewPlugin.favorites_read_url,
            resource_class_args=(s.favorite_service, s.display_service, s.profile_service),
        )
        self.api.add_resource.assert_any_call(
            FavoritesWrite,
            JsonViewPlugin.favorites_write_url,
            resource_class_args=(s.favorite_service,),
        )

    def test_that_load_with_no_personal_service_does_not_add_route(self):
        JsonViewPlugin().load({'config': {},
                               'http_namespace': Mock(),
                               'api': self.api,
                               'services': {}})

        assert_that(self.api.add_resource.call_args_list, not_(has_item(call(Personal, ANY))))

    def test_that_load_adds_the_personal_routes(self):
        dependencies = {
            'http_namespace': Mock(),
            'api': self.api,
            'services': {
                'personal': s.personal_service,
                'favorites': s.favorites_service,
                'display': s.display_service,
                'profile': s.profile_service,
            },
        }

        JsonViewPlugin().load(dependencies)

        print(self.api.add_resource.call_args_list)
        self.api.add_resource.assert_any_call(
            Personal,
            JsonViewPlugin.personal_url,
            resource_class_args=(
                s.personal_service,
                s.favorites_service,
                s.display_service,
                s.profile_service,
            ),
        )


class TestFormatResult(unittest.TestCase):

    def setUp(self):
        self.source_name = 'my_source'
        self.xivo_id = 'my_xivo_abc'
        backend = 'my_backend'
        self.SourceResult = make_result_class(backend, self.source_name, unique_column='id')

    def test_that_format_results_adds_columns_headers(self):
        display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, '', 'lastname'),
            DisplayColumn(None, 'status', None, None),
            DisplayColumn('Number', 'office_number', None, 'telephoneNumber'),
            DisplayColumn('Country', None, 'Canada', 'country'),
        ]
        formatter = _ResultFormatter(display)

        result = formatter.format_results([], [])

        expected_headers = ['Firstname', 'Lastname', None, 'Number', 'Country']
        assert_that(result, has_entries('column_headers', expected_headers))

    def test_that_format_results_adds_columns_types(self):
        display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, '', 'lastname'),
            DisplayColumn(None, 'status', None, None),
            DisplayColumn('Number', 'office_number', None, 'telephoneNumber'),
            DisplayColumn('Country', None, 'Canada', 'country'),
            DisplayColumn(None, 'favorite', None, None),
        ]
        formatter = _ResultFormatter(display)

        result = formatter.format_results([], [])

        expected_types = [None, None, 'status', 'office_number', None, 'favorite']
        assert_that(result, has_entries('column_types', expected_types))

    def test_that_format_results_adds_results(self):
        result1 = self.SourceResult({'id': 1,
                                     'firstname': 'Alice',
                                     'lastname': 'AAA',
                                     'telephoneNumber': '5555555555'},
                                    self.xivo_id, None, None, None, None)
        result2 = self.SourceResult({'id': 'user_id',
                                     'firstname': 'Bob',
                                     'lastname': 'BBB',
                                     'telephoneNumber': '5555556666'},
                                    self.xivo_id, 'agent_id', 'user_id', UUID1, 'endpoint_id')
        display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, '', 'lastname'),
            DisplayColumn(None, 'status', None, None),
            DisplayColumn('Number', 'office_number', None, 'telephoneNumber'),
            DisplayColumn('Country', None, 'Canada', 'country')
        ]
        formatter = _ResultFormatter(display)

        result = formatter.format_results([result1, result2], [])

        assert_that(result, has_entries('results', [
            {
                'column_values': ['Alice', 'AAA', None, '5555555555', 'Canada'],
                'relations': {'xivo_id': self.xivo_id,
                              'agent_id': None,
                              'user_id': None,
                              'user_uuid': None,
                              'endpoint_id': None,
                              'source_entry_id': '1'},
                'source': self.source_name,
                'backend': 'my_backend',
            },
            {
                'column_values': ['Bob', 'BBB', None, '5555556666', 'Canada'],
                'relations': {'xivo_id': self.xivo_id,
                              'agent_id': 'agent_id',
                              'user_id': 'user_id',
                              'user_uuid': UUID1,
                              'endpoint_id': 'endpoint_id',
                              'source_entry_id': 'user_id'},
                'source': self.source_name,
                'backend': 'my_backend',
            },
        ]))

    def test_that_format_results_marks_favorites(self):
        result1 = self.SourceResult({'id': 1,
                                     'firstname': 'Alice',
                                     'lastname': 'AAA',
                                     'telephoneNumber': '5555555555'},
                                    self.xivo_id, None, 1, UUID1, None)
        result2 = self.SourceResult({'id': 2,
                                     'firstname': 'Bob',
                                     'lastname': 'BBB',
                                     'telephoneNumber': '5555556666'},
                                    self.xivo_id, 'agent_id', 2, UUID2, 'endpoint_id')
        display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, '', 'lastname'),
            DisplayColumn('Number', 'office_number', None, 'telephoneNumber'),
            DisplayColumn('Favorite', 'favorite', None, None),
        ]
        formatter = _ResultFormatter(display)

        result = formatter.format_results([result1, result2], {'my_source': ['2'],
                                                               'my_other_source': ['1', '2', '3']})

        assert_that(result, has_entry('results', contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555', False)),
            has_entry('column_values', contains('Bob', 'BBB', '5555556666', True)))))

    def test_that_format_results_marks_personal(self):
        result1 = self.SourceResult({'id': 1,
                                     'firstname': 'Alice',
                                     'lastname': 'AAA',
                                     'telephoneNumber': '5555555555'},
                                    self.xivo_id, None, 1, UUID1, None)
        result2 = self.SourceResult({'id': 2,
                                     'firstname': 'Bob',
                                     'lastname': 'BBB',
                                     'telephoneNumber': '5555556666'},
                                    self.xivo_id, 'agent_id', 2, UUID2, 'endpoint_id')
        result3 = make_result_class(
            'personal',
            'personal_source',
            unique_column='id',
            is_personal=True,
            is_deletable=True)({
                'id': 'my-id',
                'firstname': 'Charlie',
                'lastname': 'CCC',
                'telephoneNumber': '5555557777'
            }, self.xivo_id, None, None, None)

        display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, '', 'lastname'),
            DisplayColumn('Number', 'office_number', None, 'telephoneNumber'),
            DisplayColumn('Personal', 'personal', None, None),
        ]
        formatter = _ResultFormatter(display)

        result = formatter.format_results([result1, result2, result3], {})

        assert_that(result, has_entry('results', contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555', False)),
            has_entry('column_values', contains('Bob', 'BBB', '5555556666', False)),
            has_entry('column_values', contains('Charlie', 'CCC', '5555557777', True)))))
