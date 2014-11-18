# -*- coding: utf-8 -*-

# Copyright (C) 2014 Avencall
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
from hamcrest import equal_to


class TestXivoUser(BaseDirdIntegrationTest):

    asset = 'xivo_users'
    uuid = "6fa459ea-ee8a-3ca4-894e-db77e160355e"

    def test_that_the_lookup_returns_the_expected_result(self):
        result = self.lookup('dyl', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains('Bob', 'Dylan', '1000', None))

    def test_that_relations_are_present(self):
        result = self.lookup('john', 'default')

        relations = result['results'][0]['relations']
        assert_that(relations, equal_to({'agent': {'id': 3,
                                                   'xivo_id': self.uuid},
                                         'endpoint': {'id': 2,
                                                      'xivo_id': self.uuid},
                                         'user': {'id': 1,
                                                  'xivo_id': self.uuid}}))

    def test_no_result(self):
        result = self.lookup('frack', 'default')

        assert_that(result['results'], contains())


class TestXivoUserMultipleXivo(BaseDirdIntegrationTest):

    asset = 'xivo_users_multiple_xivo'

    def test_lookup_multiple_xivo(self):
        result = self.lookup('ar', 'default')

        expected_result = [
            {
                'column_values': ['Charles', 'European', '9012', None],
                'relations': {'agent': None,
                              'endpoint': {'id': 42,
                                           'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77e1europe'},
                              'user': {'id': 100,
                                       'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77e1europe'}},
                'source': 'xivo_europe',
            },
            {
                'column_values': ['Mary', 'Sue', '1465', None],
                'relations': {'agent': None,
                              'endpoint': {'id': 2,
                                           'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica'},
                              'user': {'id': 2,
                                       'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica'}},
                'source': 'xivo_america',
            },
            {
                'column_values': ['Charles', 'Kenedy', '', None],
                'relations': {'agent': None,
                              'endpoint': None,
                              'user': {'id': 100,
                                       'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica'}},
                'source': 'xivo_america',
            }
        ]

        assert_that(result['results'], contains_inanyorder(*expected_result))
