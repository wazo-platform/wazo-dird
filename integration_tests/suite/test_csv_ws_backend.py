# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, contains, empty, has_entries

from .helpers.base import DirdAssetRunningTestCase
from .base_dird_integration_test import BackendWrapper


class _BaseCSVWSBackend(DirdAssetRunningTestCase):
    def setUp(self):
        self.backend = BackendWrapper('csv_ws', {'config': self.backend_config()})


class TestCSVWSBackend(_BaseCSVWSBackend):

    asset = 'csv_ws_utf8_with_pipes_with_ssl'

    def setUp(self):
        super().setUp()
        self._andree_anne = {
            'id': '1',
            'firstname': 'Andrée-Anne',
            'lastname': 'Smith',
            'number': '5551231111',
        }
        self._benoit = {
            'id': '42',
            'firstname': 'Benoît',
            'lastname': 'Malone',
            'number': '5551232222',
        }

    def backend_config(self):
        return {
            'type': 'csv_ws',
            'name': 'my_csv',
            'list_url': 'https://localhost:{port}/ws'.format(
                port=self.service_port(9485, 'ws')
            ),
            'lookup_url': 'https://localhost:{port}/ws'.format(
                port=self.service_port(9485, 'ws')
            ),
            'verify_certificate': False,
            'delimiter': "|",
            'unique_column': 'id',
            'searched_columns': ['firstname', 'lastname'],
            'first_matched_columns': ['number'],
            'format_columns': {'reverse': '{firstname} {lastname}'},
        }

    def test_that_verify_certificate_false(self):
        results = self.backend.search('Ben')

        assert_that(results, contains(has_entries(**self._benoit)))

    def test_that_searching_for_result_with_non_ascii(self):
        results = self.backend.search('dré')

        assert_that(results, contains(has_entries(**self._andree_anne)))

    def test_reverse_lookup(self):
        result = self.backend.first('5551231111')

        assert_that(result, has_entries(**self._andree_anne))

    def test_that_no_result_returns_an_empty_list(self):
        results = self.backend.search('henry')

        assert_that(results, empty())

    def test_that_list_returns_a_contact(self):
        unknown_id = '12'

        result = self.backend.list([self._benoit['id'], unknown_id])

        assert_that(result, contains(has_entries(**self._benoit)))


class TestCSVWSBackendComa(_BaseCSVWSBackend):

    asset = 'csv_ws_iso88591_with_coma'

    def setUp(self):
        super().setUp()
        self._andree_anne = {
            'id': '1',
            'firstname': 'Andrée-Anne',
            'lastname': 'Smith',
            'number': '5551231111',
        }
        self._benoit = {
            'id': '42',
            'firstname': 'Benoît',
            'lastname': 'Malone',
            'number': '5551232222',
        }

    def backend_config(self):
        return {
            'type': 'csv_ws',
            'name': 'my_csv',
            'list_url': 'http://localhost:{port}/ws'.format(
                port=self.service_port(9485, 'ws')
            ),
            'lookup_url': 'http://localhost:{port}/ws'.format(
                port=self.service_port(9485, 'ws')
            ),
            'delimiter': ',',
            'unique_column': 'id',
            'searched_columns': ['firstname', 'lastname'],
        }

    def test_that_searching_for_result_with_non_ascii(self):
        results = self.backend.search('dré')

        assert_that(results, contains(has_entries(**self._andree_anne)))

    def test_that_no_result_returns_an_empty_list(self):
        results = self.backend.search('henry')

        assert_that(results, empty())

    def test_that_list_returns_a_contact(self):
        unknown_id = 55

        result = self.backend.list([self._benoit['id'], unknown_id])

        assert_that(result, contains(has_entries(**self._benoit)))
