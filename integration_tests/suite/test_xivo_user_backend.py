# -*- coding: utf-8 -*-

# Copyright (C) 2014-2015 Avencall
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

import time

from .base_dird_integration_test import BaseDirdIntegrationTest
from .base_dird_integration_test import VALID_UUID

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import equal_to
from hamcrest import has_entry


class TestXivoUser(BaseDirdIntegrationTest):

    asset = 'xivo_users'
    uuid = "6fa459ea-ee8a-3ca4-894e-db77e160355e"

    def test_that_the_lookup_returns_the_expected_result(self):
        result = self.lookup('dyl', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains('Bob', 'Dylan', '1000', None))

    def test_that_the_reverse_lookup_returns_the_expected_result(self):
        result = self.reverse('1000', 'default', VALID_UUID)

        assert_that(result['display'], equal_to('Bob Dylan'))

    def test_that_relations_are_present(self):
        result = self.lookup('john', 'default')

        relations = result['results'][0]['relations']
        assert_that(relations, equal_to({'xivo_id': self.uuid,
                                         'agent_id': 3,
                                         'endpoint_id': 2,
                                         'user_id': 1,
                                         'source_entry_id': '1'}))

    def test_no_result(self):
        result = self.lookup('frack', 'default')

        assert_that(result['results'], contains())


class TestXivoUserNoConfd(BaseDirdIntegrationTest):

    asset = 'xivo_users_no_confd'

    def test_given_no_confd_when_lookup_then_returns_no_results(self):
        result = self.lookup('dyl', 'default')
        assert_that(result['results'], contains())


class TestXivoUserLateConfd(BaseDirdIntegrationTest):

    asset = 'xivo_users_late_confd'

    def test_given_confd_slow_to_start_when_lookup_then_first_returns_no_results_then_return_right_result(self):
        # dird is not stuck on a late confd
        result = self.lookup('dyl', 'default')
        assert_that(result['results'], contains())

        # once confd is started we can retrieve its results
        max_tries = 10
        for _ in xrange(max_tries):
            try:
                result = self.lookup('dyl', 'default')
                assert_that(result['results'],
                            contains(has_entry('column_values',
                                               contains('Bob', 'Dylan', '1000', None))))
                return
            except AssertionError as e:
                time.sleep(1)
                exception = e

        raise exception


class TestXivoUserMultipleXivo(BaseDirdIntegrationTest):

    asset = 'xivo_users_multiple_xivo'

    def test_lookup_multiple_xivo(self):
        result = self.lookup('ar', 'default')

        expected_result = [
            {
                'column_values': ['Charles', 'European', '9012', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77e1europe',
                              'agent_id': None,
                              'endpoint_id': 42,
                              'user_id': 100,
                              'source_entry_id': '100'},
                'source': 'xivo_europe',
            },
            {
                'column_values': ['Mary', 'Sue', '1465', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': None,
                              'endpoint_id': 2,
                              'user_id': 2,
                              'source_entry_id': '2'},
                'source': 'xivo_america',
            },
            {
                'column_values': ['Charles', 'Kenedy', '', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': None,
                              'endpoint_id': None,
                              'user_id': 100,
                              'source_entry_id': '100'},
                'source': 'xivo_america',
            }
        ]

        assert_that(result['results'], contains_inanyorder(*expected_result))

    def test_favorites_multiple_xivo(self):
        self.put_favorite('xivo_america', 1)
        self.put_favorite('xivo_asia', 1)

        result = self.favorites('default')

        expected_result = [
            {
                'column_values': ['Alice', None, '6543', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77e160asia',
                              'agent_id': 3,
                              'endpoint_id': 2,
                              'user_id': 1,
                              'source_entry_id': '1'},
                'source': 'xivo_asia',
            },
            {
                'column_values': ['John', 'Doe', '1234', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': 3,
                              'endpoint_id': 2,
                              'user_id': 1,
                              'source_entry_id': '1'},
                'source': 'xivo_america',
            }
        ]

        assert_that(result['results'], contains_inanyorder(*expected_result))


class TestXivoUserMultipleXivoOneMissing(BaseDirdIntegrationTest):

    asset = 'xivo_users_missing_one_xivo'

    def test_lookup_multiple_xivo(self):
        result = self.lookup('john', 'default')

        expected_result = [
            {
                'column_values': ['John', 'Doe', '1234', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': 3,
                              'endpoint_id': 2,
                              'user_id': 1,
                              'source_entry_id': '1'},
                'source': 'xivo_america',
            },
        ]

        assert_that(result['results'], contains_inanyorder(*expected_result))


class TestXivoUserMultipleXivoOne404(BaseDirdIntegrationTest):

    asset = 'xivo_users_two_working_one_404'

    def test_lookup_multiple_xivo(self):
        result = self.lookup('ar', 'default')

        expected_result = [
            {
                'column_values': ['Mary', 'Sue', '1465', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': None,
                              'endpoint_id': 2,
                              'user_id': 2,
                              'source_entry_id': '2'},
                'source': 'xivo_america',
            },
            {
                'column_values': ['Charles', 'Kenedy', '', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': None,
                              'endpoint_id': None,
                              'user_id': 100,
                              'source_entry_id': '100'},
                'source': 'xivo_america',
            }
        ]

        assert_that(result['results'], contains_inanyorder(*expected_result))


class TestXivoUserMultipleXivoOneTimeout(BaseDirdIntegrationTest):

    asset = 'xivo_users_two_working_one_timeout'

    def test_lookup_multiple_xivo(self):
        result = self.lookup('ar', 'default')

        expected_result = [
            {
                'column_values': ['Mary', 'Sue', '1465', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': None,
                              'endpoint_id': 2,
                              'user_id': 2,
                              'source_entry_id': '2'},
                'source': 'xivo_america',
            },
            {
                'column_values': ['Charles', 'Kenedy', '', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': None,
                              'endpoint_id': None,
                              'user_id': 100,
                              'source_entry_id': '100'},
                'source': 'xivo_america',
            }
        ]

        assert_that(result['results'], contains_inanyorder(*expected_result))
