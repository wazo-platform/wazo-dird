# -*- coding: utf-8 -*-

# Copyright (C) 2015 Avencall
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

from .base_dird_integration_test import BaseDirdIntegrationTest

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import has_entry


class TestCSVBackend(BaseDirdIntegrationTest):

    asset = 'csv_with_multiple_displays'

    def test_that_searching_for_lice_return_Alice(self):
        result = self.lookup('lice', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains('Alice', 'AAA', '5555555555'))

    def test_that_asking_csv_favorites_returns_contacts(self):
        self.put_favorite('my_csv', '1')
        self.put_favorite('my_csv', '3')

        result = self.favorites('default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'AAA', '5555555555')),
            has_entry('column_values', contains('Charles', 'CCC', '555123555'))))


class TestCSVNoUnique(BaseDirdIntegrationTest):

    asset = 'csv_with_no_unique_column'

    def test_lookup_should_work_without_unique_column(self):
        result = self.lookup('lice', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains('Alice', 'AAA', '5555555555'))


class TestCSVWithAccents(BaseDirdIntegrationTest):

    asset = 'csv_with_no_unique_column'

    def test_lookup_with_accents_in_term(self):
        result = self.lookup('pép', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains(u'Pépé', u'lol', u'555'))

    def test_lookup_with_accents_in_the_result(self):
        result = self.lookup('lol', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains(u'Pépé', u'lol', u'555'))


class TestCSVSeperator(BaseDirdIntegrationTest):

    asset = 'csv_with_pipes'

    def test_lookup_with_pipe(self):
        result = self.lookup('al', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains(u'Alice', u'AAA', u'5555555555'))
