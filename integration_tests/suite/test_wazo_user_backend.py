# Copyright 2014-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest.mock import Mock

from hamcrest import (
    assert_that,
    contains_exactly,
    contains_inanyorder,
    empty,
    equal_to,
    has_entries,
    has_entry,
)
from wazo_test_helpers import until

from .helpers.base import BaseDirdIntegrationTest, DirdAssetRunningTestCase
from .helpers.config import new_wazo_users_config, new_wazo_users_multiple_wazo_config
from .helpers.constants import MAIN_TENANT, VALID_TOKEN_MAIN_TENANT
from .helpers.utils import BackendWrapper


class TestWazoUser(DirdAssetRunningTestCase):
    asset = 'wazo_confd'
    uuid = "6fa459ea-ee8a-3ca4-894e-db77e160355e"

    def setUp(self):
        super().setUp()
        self.backend = BackendWrapper(
            'wazo', {'config': self.backend_config(), 'api': Mock()}
        )
        self._dylan = {
            'id': 42,
            'firstname': 'Bob',
            'lastname': 'Dylan',
            'exten': '1000',
            'voicemail_number': '1234',
        }
        self._bob = {
            'id': 1,
            'firstname': 'John',
            'lastname': 'Doe',
            'exten': '1234',
        }
        self._picasso = {
            "id": 43,
            "firstname": "Pablo Ruiz",
            "lastname": "Picasso",
            "exten": "1001",
            "email": "pablo.ruiz.picasso@example.org",
            "voicemail_number": "1235",
        }

    def tearDown(self):
        self.backend.unload()

    def backend_config(self):
        return {
            'uuid': '39679e98-a33a-4bc7-81b6-c581a61b41a5',
            'type': 'wazo',
            'tenant_uuid': MAIN_TENANT,
            'name': 'wazo_america',
            'searched_columns': ['firstname', 'lastname', 'full_name'],
            'first_matched_columns': ['exten'],
            'auth': {
                'host': '127.0.0.1',
                'port': self.service_port(9497, 'auth'),
                'prefix': None,
                'https': False,
            },
            'confd': {
                'host': '127.0.0.1',
                'port': self.service_port(9486, 'confd'),
                'prefix': None,
                'https': False,
                'version': '1.1',
            },
            'format_columns': {
                'number': "{exten}",
                'reverse': "{firstname} {lastname}",
                'voicemail': "{voicemail_number}",
            },
        }

    def test_that_the_lookup_returns_the_expected_result(self):
        search_terms = ['dyl', 'dylan', 'bob', 'bob ', 'bob dyl', ' dyl']
        for term in search_terms:
            results = self.backend.search(term)

            assert_that(results, contains_exactly(has_entries(**self._dylan)))

        search_terms = [
            'pic',
            'picasso',
            'pablo',
            'pablo ruiz ',
            'pablo ruiz pic',
            ' picasso',
        ]
        for term in search_terms:
            results = self.backend.search(term)

            assert_that(results, contains_exactly(has_entries(**self._picasso)))

    def test_that_the_reverse_lookup_returns_the_expected_result(self):
        result = self.backend.first('1000')

        assert_that(result, has_entries(**self._dylan))

    def test_match_all_returns_the_expected_result(self):
        result = self.backend.match_all(['1000', '1234'])

        assert_that(
            result,
            contains_inanyorder(
                has_entries(**self._dylan),
                has_entries(**self._bob),
            ),
        )

    def test_that_relations_are_present(self):
        results = self.backend.search_raw('john')

        relations = results[0].relations
        assert_that(
            relations,
            equal_to(
                {
                    'xivo_id': self.uuid,
                    'agent_id': 3,
                    'endpoint_id': 2,
                    'user_id': 1,
                    'user_uuid': '7ca42f43-8bd9-4a26-acb8-cb756f42bebb',
                    'source_entry_id': '7ca42f43-8bd9-4a26-acb8-cb756f42bebb',
                }
            ),
        )

    def test_no_result(self):
        results = self.backend.search('frack')

        assert_that(results, empty())


class TestWazoUserNoConfd(BaseDirdIntegrationTest):
    asset = 'wazo_no_confd'
    config_factory = new_wazo_users_config

    def test_given_no_confd_when_lookup_then_returns_no_results(self):
        result = self.lookup('dyl', 'default')
        assert_that(result['results'], contains_exactly())


class TestWazoUserLateConfd(BaseDirdIntegrationTest):
    asset = 'wazo_users_late_confd'
    config_factory = new_wazo_users_config

    def test_no_result_until_started(self):
        # dird is not stuck on a late confd
        result = self.lookup('dyl', 'default')
        assert_that(result['results'], contains_exactly())

        self.docker_exec(['touch', '/var/local/start-confd'], service_name='america')

        def test():
            result = self.lookup('dyl', 'default')
            assert_that(
                result['results'],
                contains_exactly(
                    has_entry(
                        'column_values', contains_exactly('Bob', 'Dylan', '1000', '')
                    )
                ),
            )

        until.assert_(test, timeout=10)


class TestWazoUserMultipleWazo(BaseDirdIntegrationTest):
    asset = 'wazo_users_multiple_wazo'
    config_factory = new_wazo_users_multiple_wazo_config

    def test_lookup_multiple_wazo(self):
        result = self.lookup('ar', 'default')

        expected_result = [
            {
                'column_values': ['Charles', 'European', '9012'],
                'relations': {
                    'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77e1europe',
                    'agent_id': None,
                    'endpoint_id': 42,
                    'user_id': 100,
                    'user_uuid': 'ce36bbb4-ae97-4f7d-8a36-d82b96120418',
                    'source_entry_id': 'ce36bbb4-ae97-4f7d-8a36-d82b96120418',
                },
                'source': 'wazo_europe',
                'backend': 'wazo',
            },
            {
                'column_values': ['Mary', 'Sue', '1465'],
                'relations': {
                    'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                    'agent_id': None,
                    'endpoint_id': 2,
                    'user_id': 2,
                    'user_uuid': 'df486ed4-975b-4316-815c-e19c3c1811c4',
                    'source_entry_id': 'df486ed4-975b-4316-815c-e19c3c1811c4',
                },
                'source': 'wazo_america',
                'backend': 'wazo',
            },
            {
                'column_values': ['Charles', 'Kenedy', ''],
                'relations': {
                    'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                    'agent_id': None,
                    'endpoint_id': None,
                    'user_id': 100,
                    'user_uuid': '9dfa2706-cd85-4130-82be-c54cc15e8410',
                    'source_entry_id': '9dfa2706-cd85-4130-82be-c54cc15e8410',
                },
                'source': 'wazo_america',
                'backend': 'wazo',
            },
        ]

        assert_that(result['results'], contains_inanyorder(*expected_result))

    def test_favorites_by_user_uuid(self):
        john_doe_uuid = '7ca42f43-8bd9-4a26-acb8-cb756f42bebb'

        with self.favorite('wazo_america', john_doe_uuid):
            result = self.favorites('default')

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entries(
                    source='wazo_america',
                    column_values=contains_exactly('John', 'Doe', '1234'),
                    relations=has_entries(source_entry_id=john_doe_uuid),
                )
            ),
        )

    def test_favorite_with_an_invalid_contact_id_is_refused(self):
        # nothing else checks the contact id, so an id no lookup could ever
        # return must not be storable
        result = self.put_favorite_result(
            'wazo_america', 'not-a-contact-id', token=VALID_TOKEN_MAIN_TENANT
        )

        assert_that(result.status_code, equal_to(400))

    def test_a_favorited_contact_is_marked_in_a_lookup(self):
        # the marking compares the stored contact id with the source_entry_id
        # a lookup returns; nothing translates between them, so the write path
        # and the backend have to agree on the form
        john_doe_uuid = '7ca42f43-8bd9-4a26-acb8-cb756f42bebb'

        before = self.lookup('John', 'marks_favorites')
        assert_that(
            before['results'],
            contains_exactly(
                has_entries(column_values=contains_exactly('John', False))
            ),
        )

        with self.favorite('wazo_america', john_doe_uuid):
            after = self.lookup('John', 'marks_favorites')

        assert_that(
            after['results'],
            contains_exactly(
                has_entries(
                    column_values=contains_exactly('John', True),
                    relations=has_entries(source_entry_id=john_doe_uuid),
                )
            ),
        )

    def test_favorites_multiple_wazo(self):
        # a client that predates the uuid switch still sends the confd id;
        # it must be resolved to the uuid of the user of *that* wazo
        self.put_favorite('wazo_america', 1)
        self.put_favorite('wazo_asia', 1)

        result = self.favorites('default')

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entries(
                    source='wazo_asia',
                    column_values=contains_exactly('Alice', None, '6543'),
                    relations=has_entries(
                        source_entry_id='7c12f90e-7391-4514-b482-5b75b57772e1'
                    ),
                ),
                has_entries(
                    source='wazo_america',
                    column_values=contains_exactly('John', 'Doe', '1234'),
                    relations=has_entries(
                        source_entry_id='7ca42f43-8bd9-4a26-acb8-cb756f42bebb'
                    ),
                ),
            ),
        )


class TestWazoUserMultipleWazoOneMissing(BaseDirdIntegrationTest):
    asset = 'wazo_users_missing_one_wazo'
    config_factory = new_wazo_users_multiple_wazo_config

    def test_lookup_multiple_wazo(self):
        result = self.lookup('john', 'default')

        expected_result = [
            {
                'column_values': ['John', 'Doe', '1234'],
                'relations': {
                    'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                    'agent_id': 3,
                    'endpoint_id': 2,
                    'user_id': 1,
                    'user_uuid': '7ca42f43-8bd9-4a26-acb8-cb756f42bebb',
                    'source_entry_id': '7ca42f43-8bd9-4a26-acb8-cb756f42bebb',
                },
                'source': 'wazo_america',
                'backend': 'wazo',
            }
        ]

        assert_that(result['results'], contains_inanyorder(*expected_result))


class TestWazoUserMultipleWazoOne404(BaseDirdIntegrationTest):
    asset = 'wazo_users_two_working_one_404'
    config_factory = new_wazo_users_multiple_wazo_config

    def test_lookup_multiple_wazo(self):
        result = self.lookup('ar', 'default')

        expected_result = [
            {
                'column_values': ['Mary', 'Sue', '1465'],
                'relations': {
                    'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                    'agent_id': None,
                    'endpoint_id': 2,
                    'user_id': 2,
                    'user_uuid': 'df486ed4-975b-4316-815c-e19c3c1811c4',
                    'source_entry_id': 'df486ed4-975b-4316-815c-e19c3c1811c4',
                },
                'source': 'wazo_america',
                'backend': 'wazo',
            },
            {
                'column_values': ['Charles', 'Kenedy', ''],
                'relations': {
                    'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                    'agent_id': None,
                    'endpoint_id': None,
                    'user_id': 100,
                    'user_uuid': '9dfa2706-cd85-4130-82be-c54cc15e8410',
                    'source_entry_id': '9dfa2706-cd85-4130-82be-c54cc15e8410',
                },
                'source': 'wazo_america',
                'backend': 'wazo',
            },
        ]

        assert_that(result['results'], contains_inanyorder(*expected_result))


class TestWazoUserMultipleWazoOneTimeout(BaseDirdIntegrationTest):
    asset = 'wazo_users_two_working_one_timeout'
    config_factory = new_wazo_users_multiple_wazo_config

    def test_lookup_multiple_wazo(self):
        result = self.lookup('ar', 'default')

        expected_result = [
            {
                'column_values': ['Mary', 'Sue', '1465'],
                'relations': {
                    'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                    'agent_id': None,
                    'endpoint_id': 2,
                    'user_id': 2,
                    'user_uuid': 'df486ed4-975b-4316-815c-e19c3c1811c4',
                    'source_entry_id': 'df486ed4-975b-4316-815c-e19c3c1811c4',
                },
                'source': 'wazo_america',
                'backend': 'wazo',
            },
            {
                'column_values': ['Charles', 'Kenedy', ''],
                'relations': {
                    'xivo_id': '6fa459ea-ee8a-3ca4-894e-db77eamerica',
                    'agent_id': None,
                    'endpoint_id': None,
                    'user_id': 100,
                    'user_uuid': '9dfa2706-cd85-4130-82be-c54cc15e8410',
                    'source_entry_id': '9dfa2706-cd85-4130-82be-c54cc15e8410',
                },
                'source': 'wazo_america',
                'backend': 'wazo',
            },
        ]

        assert_that(result['results'], contains_inanyorder(*expected_result))
