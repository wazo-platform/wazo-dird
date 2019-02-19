# Copyright 2014-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from mock import Mock
from hamcrest import (
    assert_that,
    contains,
    contains_inanyorder,
    empty,
    equal_to,
    has_entries,
    has_entry,
)

from xivo_test_helpers import until

from .helpers.fixtures import http as fixtures
from .base_dird_integration_test import (
    BaseDirdIntegrationTest,
    BackendWrapper,
)

WAZO_ASIA = {
    'name': 'wazo_asia',
    'auth': {'host': 'auth', 'username': 'foo', 'password': 'bar'},
    'confd': {'host': 'asia', 'port': 9486, 'https': False},
    'searched_columns': ['firstname', 'lastname'],
}
WAZO_AMERICA = {
    'name': 'wazo_america',
    'auth': {'host': 'auth', 'username': 'foo', 'password': 'bar'},
    'confd': {'host': 'confd', 'port': 9486, 'https': False},
    'searched_columns': ['firstname', 'lastname'],
}
WAZO_EUROPE = {
    'name': 'wazo_europe',
    'auth': {'host': 'auth', 'username': 'foo', 'password': 'bar'},
    'confd': {'host': 'europe', 'port': 9486, 'https': False},
    'searched_columns': ['firstname', 'lastname'],
}


class TestWazoUser(BaseDirdIntegrationTest):

    asset = 'wazo_users'
    uuid = "6fa459ea-ee8a-3ca4-894e-db77e160355e"

    def setUp(self):
        super().setUp()
        self.backend = BackendWrapper(
            'wazo',
            {
                'config': self.backend_config(),
                'api': Mock(),
            }
        )
        self._dylan = {'id': 42,
                       'firstname': 'Bob',
                       'lastname': 'Dylan',
                       'exten': '1000',
                       'voicemail_number': '1234'}

    def tearDown(self):
        self.backend.unload()

    def backend_config(self):
        return {
            'type': 'wazo',
            'name': 'wazo_america',
            'searched_columns': ['firstname', 'lastname'],
            'first_matched_columns': ['exten'],
            'auth': {
                'host': 'localhost',
                'port': self.service_port(9497, 'auth'),
                'verify_certificate': False,
            },
            'confd': {
                'host': 'localhost',
                'port': self.service_port(9486, 'confd'),
                'version': '1.1',
                'https': False,
            },
            'format_columns': {
                'number': "{exten}",
                'reverse': "{firstname} {lastname}",
                'voicemail': "{voicemail_number}",
            },
        }

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


class TestWazoUserNoConfd(BaseDirdIntegrationTest):

    asset = 'wazo_users_no_confd'

    def test_given_no_confd_when_lookup_then_returns_no_results(self):
        result = self.lookup('dyl', 'default')
        assert_that(result['results'], contains())


class TestWazoUserLateConfd(BaseDirdIntegrationTest):

    asset = 'wazo_users_late_confd'


    @fixtures.wazo_source(**WAZO_AMERICA)
    def test_no_result_until_started(self, source):
        # dird is not stuck on a late confd
        result = self.lookup('dyl', 'default')
        assert_that(result['results'], contains())

        def test():
            result = self.lookup('dyl', 'default')
            assert_that(result['results'],
                        contains(has_entry('column_values',
                                           contains('Bob', 'Dylan', '1000', ''))))

        until.assert_(test, tries=10)


class TestWazoUserMultipleWazo(BaseDirdIntegrationTest):

    asset = 'wazo_users_multiple_wazo'

    def setUp(self):
        asia = self.client.wazo_source.create(WAZO_ASIA)
        america = self.client.wazo_source.create(WAZO_AMERICA)
        europe = self.client.wazo_source.create(WAZO_EUROPE)
        self._source_uuids = [asia['uuid'], america['uuid'], europe['uuid']]

    def tearDown(self):
        for uuid in self._source_uuids:
            try:
                self.client.wazo_source.delete(uuid)
            except Exception:
                continue

    def test_lookup_multiple_wazo(self):
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
                'source': 'wazo_europe',
            },
            {
                'column_values': ['Mary', 'Sue', '1465', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': None,
                              'endpoint_id': 2,
                              'user_id': 2,
                              'user_uuid': 'df486ed4-975b-4316-815c-e19c3c1811c4',
                              'source_entry_id': '2'},
                'source': 'wazo_america',
            },
            {
                'column_values': ['Charles', 'Kenedy', '', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': None,
                              'endpoint_id': None,
                              'user_id': 100,
                              'user_uuid': '9dfa2706-cd85-4130-82be-c54cc15e8410',
                              'source_entry_id': '100'},
                'source': 'wazo_america',
            }
        ]

        assert_that(result['results'], contains_inanyorder(*expected_result))

    def test_favorites_multiple_wazo(self):
        self.put_favorite('wazo_america', 1)
        self.put_favorite('wazo_asia', 1)

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
                'source': 'wazo_asia',
            },
            {
                'column_values': ['John', 'Doe', '1234', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': 3,
                              'endpoint_id': 2,
                              'user_id': 1,
                              'user_uuid': '7ca42f43-8bd9-4a26-acb8-cb756f42bebb',
                              'source_entry_id': '1'},
                'source': 'wazo_america',
            }
        ]

        assert_that(result['results'], contains_inanyorder(*expected_result))


class TestWazoUserMultipleWazoOneMissing(BaseDirdIntegrationTest):

    asset = 'wazo_users_missing_one_wazo'

    def test_lookup_multiple_wazo(self):
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
                'source': 'wazo_america',
            },
        ]

        assert_that(result['results'], contains_inanyorder(*expected_result))


class TestWazoUserMultipleWazoOne404(BaseDirdIntegrationTest):

    asset = 'wazo_users_two_working_one_404'

    def test_lookup_multiple_wazo(self):
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
                'source': 'wazo_america',
            },
            {
                'column_values': ['Charles', 'Kenedy', '', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': None,
                              'endpoint_id': None,
                              'user_id': 100,
                              'user_uuid': '9dfa2706-cd85-4130-82be-c54cc15e8410',
                              'source_entry_id': '100'},
                'source': 'wazo_america',
            }
        ]

        assert_that(result['results'], contains_inanyorder(*expected_result))


class TestWazoUserMultipleWazoOneTimeout(BaseDirdIntegrationTest):

    asset = 'wazo_users_two_working_one_timeout'

    def test_lookup_multiple_wazo(self):
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
                'source': 'wazo_america',
            },
            {
                'column_values': ['Charles', 'Kenedy', '', None],
                'relations': {'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                              'agent_id': None,
                              'endpoint_id': None,
                              'user_id': 100,
                              'user_uuid': '9dfa2706-cd85-4130-82be-c54cc15e8410',
                              'source_entry_id': '100'},
                'source': 'wazo_america',
            }
        ]

        assert_that(result['results'], contains_inanyorder(*expected_result))
