# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Avencall
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

import unittest

from xivo_dird.plugins.csv_ws import CSVWSPlugin

from hamcrest import assert_that, is_, empty
from mock import patch
from mock import sentinel as s


class TestCSVWSPlugin(unittest.TestCase):

    def test_that_a_missing_lookup_url_fails_on_load(self):
        source = CSVWSPlugin()

        self.assertRaises(Exception, source.load, {})

    @patch('xivo_dird.plugins.csv_ws.requests')
    def test_that_search_queries_the_lookup_url(self, mocked_requests):
        lookup_url = u'http://example.com:8000/ws?search={term}'
        config = {'config': {'lookup_url': lookup_url,
                             'name': 'my-ws-source',
                             'timeout': s.timeout}}
        term = u'dédé'
        expected_url = lookup_url.format(term=term)

        source = CSVWSPlugin()
        source.load(config)

        list(source.search(term))

        mocked_requests.get.assert_called_once_with(expected_url, timeout=s.timeout)

    def test_that_list_returns_an_empty_list_if_no_unique_column(self):
        config = {'config': {'lookup_url': 'the_lookup_url',
                             'name': 'my-ws-source',
                             'timeout': s.timeout}}

        source = CSVWSPlugin()
        source.load(config)

        result = list(source.list([1, 2, 3]))

        assert_that(result, is_(empty()))

    def test_that_list_returns_an_empty_list_if_no_list_url(self):
        config = {'config': {'lookup_url': 'the_lookup_url',
                             'unique_column': 'id',
                             'name': 'my-ws-source',
                             'timeout': s.timeout}}

        source = CSVWSPlugin()
        source.load(config)

        result = list(source.list([1, 2, 3]))

        assert_that(result, is_(empty()))

    @patch('xivo_dird.plugins.csv_ws.requests')
    def test_that_list_queries_the_list_url(self, mocked_requests):
        config = {'config': {'list_url': 'the_list_url',
                             'lookup_url': 'the_lookup_url',
                             'unique_column': 'id',
                             'name': 'my-ws-source',
                             'timeout': s.timeout}}

        source = CSVWSPlugin()
        source.load(config)

        list(source.list([1, 2, 3]))

        mocked_requests.get.assert_called_once_with('the_list_url', timeout=s.timeout)
