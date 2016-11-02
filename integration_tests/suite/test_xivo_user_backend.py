# -*- coding: utf-8 -*-

# Copyright (C) 2014-2016 Avencall
# Copyright (C) 2016 Proformatique, Inc.
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

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import equal_to
from hamcrest import empty
from hamcrest import has_entry
from hamcrest import has_entries

from xivo_test_helpers import until

from .base_dird_integration_test import absolute_file_name, BaseDirdIntegrationTest, BackendWrapper


class _BaseXiVOUserBackendTestCase(BaseDirdIntegrationTest):

    def setUp(self):
        config_file = absolute_file_name(self.asset, self.source_config)
        with open(config_file) as f:
            config = {'config': yaml.load(f)}
        self.backend = BackendWrapper('xivo', config)


class TestXivoUser(_BaseXiVOUserBackendTestCase):

    asset = 'xivo_users'
    uuid = "6fa459ea-ee8a-3ca4-894e-db77e160355e"
    source_config = 'etc/xivo-dird/sources.d/america.yml'

    def setUp(self):
        super(TestXivoUser, self).setUp()
        self._dylan = {'id': 42,
                       'firstname': 'Bob',
                       'lastname': 'Dylan',
                       'exten': '1000',
                       'voicemail_number': '1234'}

    def test_that_the_lookup_returns_the_expected_result(self):
        results = self.backend.search('dyl')

        assert_that(results, contains(has_entries(**self._dylan)))

    def test_that_the_reverse_lookup_returns_the_expected_result(self):
        result = self.backend.first('1000')

        assert_that(result, has_entries(**self._dylan))

    def test_that_relations_are_present(self):
        results = self.backend.search_raw('john')

        relations = results[0].relations
        assert_that(relations, equal_to({'xivo_id': self.uuid,
                                         'agent_id': 3,
                                         'endpoint_id': 2,
                                         'user_id': 1,
                                         'user_uuid': '7ca42f43-8bd9-4a26-acb8-cb756f42bebb',
                                         'source_entry_id': '1'}))

    def test_no_result(self):
        results = self.backend.search('frack')

        assert_that(results, empty())


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

        def test():
            result = self.lookup('dyl', 'default')
            assert_that(result['results'],
                        contains(has_entry('column_values',
                                           contains('Bob', 'Dylan', '1000', ''))))

        until.assert_(test, tries=10)


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
                              'user_uuid': 'ce36bbb4-ae97-4f7d-8a36-d82b96120418',
                              'source_entry_id': '100'},
                'source': 'xivo_europe',
            },
            {
                'column_values': ['Mary', 'Sue', '1465', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': None,
                              'endpoint_id': 2,
                              'user_id': 2,
                              'user_uuid': 'df486ed4-975b-4316-815c-e19c3c1811c4',
                              'source_entry_id': '2'},
                'source': 'xivo_america',
            },
            {
                'column_values': ['Charles', 'Kenedy', '', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': None,
                              'endpoint_id': None,
                              'user_id': 100,
                              'user_uuid': '9dfa2706-cd85-4130-82be-c54cc15e8410',
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
                              'user_uuid': '7c12f90e-7391-4514-b482-5b75b57772e1',
                              'source_entry_id': '1'},
                'source': 'xivo_asia',
            },
            {
                'column_values': ['John', 'Doe', '1234', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': 3,
                              'endpoint_id': 2,
                              'user_id': 1,
                              'user_uuid': '7ca42f43-8bd9-4a26-acb8-cb756f42bebb',
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
                              'user_uuid': '7ca42f43-8bd9-4a26-acb8-cb756f42bebb',
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
                              'user_uuid': 'df486ed4-975b-4316-815c-e19c3c1811c4',
                              'source_entry_id': '2'},
                'source': 'xivo_america',
            },
            {
                'column_values': ['Charles', 'Kenedy', '', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': None,
                              'endpoint_id': None,
                              'user_id': 100,
                              'user_uuid': '9dfa2706-cd85-4130-82be-c54cc15e8410',
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
                              'user_uuid': 'df486ed4-975b-4316-815c-e19c3c1811c4',
                              'source_entry_id': '2'},
                'source': 'xivo_america',
            },
            {
                'column_values': ['Charles', 'Kenedy', '', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': None,
                              'endpoint_id': None,
                              'user_id': 100,
                              'user_uuid': '9dfa2706-cd85-4130-82be-c54cc15e8410',
                              'source_entry_id': '100'},
                'source': 'xivo_america',
            }
        ]

        assert_that(result['results'], contains_inanyorder(*expected_result))
