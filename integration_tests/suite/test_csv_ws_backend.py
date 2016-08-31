# -*- coding: utf-8 -*-

# Copyright (C) 2015-2016 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import yaml

from hamcrest import (assert_that, contains, empty, has_entries)

from .base_dird_integration_test import absolute_file_name, BaseDirdIntegrationTest, BackendWrapper


class _BaseCSVWSBackend(BaseDirdIntegrationTest):

    def setUp(self):
        config_file = absolute_file_name(self.asset, self.source_config)
        with open(config_file) as f:
            config = {'config': yaml.load(f)}
        self.backend = BackendWrapper('csv_ws', config)


class TestCSVWSBackend(_BaseCSVWSBackend):

    asset = 'csv_ws_utf8_with_pipes_with_ssl'
    source_config = 'etc/xivo-dird/sources.d/my_test_csv.yml'

    def setUp(self):
        super(TestCSVWSBackend, self).setUp()
        self._andree_anne = {'id': '1',
                             'firstname': u'Andrée-Anne',
                             'lastname': 'Smith',
                             'number': '5551231111'}
        self._benoit = {'id': '42',
                        'firstname': u'Benoît',
                        'lastname': 'Malone',
                        'number': '5551232222'}

    def test_that_verify_certificate_false(self):
        results = self.backend.search(u'Ben')

        assert_that(results, contains(has_entries(**self._benoit)))

    def test_that_searching_for_result_with_non_ascii(self):
        results = self.backend.search(u'dré')

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
    source_config = 'etc/xivo-dird/sources.d/my_test_csv.yml'

    def setUp(self):
        super(TestCSVWSBackendComa, self).setUp()
        self._andree_anne = {'id': '1',
                             'firstname': u'Andrée-Anne',
                             'lastname': 'Smith',
                             'number': '5551231111'}
        self._benoit = {'id': '42',
                        'firstname': u'Benoît',
                        'lastname': 'Malone',
                        'number': '5551232222'}

    def test_that_searching_for_result_with_non_ascii(self):
        results = self.backend.search(u'dré')

        assert_that(results, contains(has_entries(**self._andree_anne)))

    def test_that_no_result_returns_an_empty_list(self):
        results = self.backend.search('henry')

        assert_that(results, empty())

    def test_that_list_returns_a_contact(self):
        unknown_id = 55

        result = self.backend.list([self._benoit['id'], unknown_id])

        assert_that(result, contains(has_entries(**self._benoit)))
