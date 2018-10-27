# Copyright 2015-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import unittest

from wazo_dird.plugins.csv_ws import CSVWSPlugin

from hamcrest import assert_that, is_, empty
from mock import patch
from mock import sentinel as s


class TestCSVWSPlugin(unittest.TestCase):

    def test_that_a_missing_lookup_url_fails_on_load(self):
        source = CSVWSPlugin()

        self.assertRaises(Exception, source.load, {})

    @patch('wazo_dird.plugins.csv_ws.requests')
    def test_that_search_queries_the_lookup_url(self, mocked_requests):
        lookup_url = 'http://example.com:8000/ws'
        config = {'config': {'lookup_url': lookup_url,
                             'name': 'my-ws-source',
                             'timeout': s.timeout,
                             'searched_columns': [
                                 'firstname',
                                 'lastname',
                             ]}}
        term = 'dédé'
        expected_params = {'firstname': 'dédé', 'lastname': 'dédé'}

        source = CSVWSPlugin()
        source.load(config)

        source.search(term)

        mocked_requests.get.assert_called_once_with(lookup_url, params=expected_params, timeout=s.timeout, verify=True)

    @patch('wazo_dird.plugins.csv_ws.requests')
    def test_that_first_match_queries_the_lookup_url(self, mocked_requests):
        lookup_url = 'http://example.com:8000/ws'
        config = {'config': {'lookup_url': lookup_url,
                             'name': 'my-ws-source',
                             'timeout': s.timeout,
                             'searched_columns': [
                                 'firstname',
                                 'lastname',
                             ],
                             'first_matched_columns': ['exten']}}
        term = '1234'
        expected_params = {'exten': '1234'}

        source = CSVWSPlugin()
        source.load(config)

        source.first_match(term)

        mocked_requests.get.assert_called_once_with(lookup_url, params=expected_params, timeout=s.timeout, verify=True)

    def test_that_list_returns_an_empty_list_if_no_unique_column(self):
        config = {'config': {'lookup_url': 'the_lookup_url',
                             'name': 'my-ws-source',
                             'timeout': s.timeout}}

        source = CSVWSPlugin()
        source.load(config)

        result = source.list([1, 2, 3])

        assert_that(result, is_(empty()))

    def test_that_list_returns_an_empty_list_if_no_list_url(self):
        config = {'config': {'lookup_url': 'the_lookup_url',
                             'unique_column': 'id',
                             'name': 'my-ws-source',
                             'timeout': s.timeout}}

        source = CSVWSPlugin()
        source.load(config)

        result = source.list([1, 2, 3])

        assert_that(result, is_(empty()))

    @patch('wazo_dird.plugins.csv_ws.requests')
    def test_that_list_queries_the_list_url(self, mocked_requests):
        config = {'config': {'list_url': 'the_list_url',
                             'lookup_url': 'the_lookup_url',
                             'unique_column': 'id',
                             'name': 'my-ws-source',
                             'timeout': s.timeout}}

        source = CSVWSPlugin()
        source.load(config)

        source.list([1, 2, 3])

        mocked_requests.get.assert_called_once_with('the_list_url', timeout=s.timeout, verify=True)
