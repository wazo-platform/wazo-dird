# Copyright 2016-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from uuid import uuid4
from mock import ANY
from hamcrest import (
    assert_that,
    contains_inanyorder,
    equal_to,
)
from xivo_test_helpers.auth import (
    AuthClient as MockAuthClient,
)
from .base_dird_integration_test import BaseDirdIntegrationTest


class TestPhonebookCRUD(BaseDirdIntegrationTest):

    asset = 'phonebook_only'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mock_auth_client = MockAuthClient('localhost', cls.service_port(9497, 'auth'))

    def test_post_in_unknown_tenant(self):
        tenants = {'items': [], 'total': 0, 'filtered': 0}
        self.mock_auth_client.set_tenants(tenants)
        valid_body = {'name': 'foobar'}
        result = self.post_phonebook('unknown', valid_body)
        assert_that(result.status_code, equal_to(404))

    def test_post_in_valid_tenant(self):
        tenants = {
            'items': [
                {
                    'uuid': str(uuid4()),
                    'name': 'valid',
                }
            ],
            'total': 1,
            'filtered': 1,
        }
        self.mock_auth_client.set_tenants(tenants)
        valid_body = {'name': 'foobar'}
        result = self.post_phonebook('valid', valid_body)
        assert_that(result.status_code, equal_to(201))

    def test_get_in_unknown_tenant(self):
        tenants = {
            'items': [
                {
                    'uuid': str(uuid4()),
                    'name': 'valid',
                }
            ],
            'total': 1,
            'filtered': 1,
        }
        self.mock_auth_client.set_tenants(tenants)

        valid_body = {'name': 'foobar'}
        phonebook = self.post_phonebook('valid', valid_body).json()

        tenants = {'items': [], 'total': 0, 'filtered': 0}
        self.mock_auth_client.set_tenants(tenants)

        result = self.get_phonebook('valid', phonebook['id'])
        assert_that(result.status_code, equal_to(404))

    def test_get_in_valid_tenant(self):
        tenants = {
            'items': [
                {
                    'uuid': str(uuid4()),
                    'name': 'valid',
                }
            ],
            'total': 1,
            'filtered': 1,
        }
        self.mock_auth_client.set_tenants(tenants)

        valid_body = {'name': 'foobar'}
        phonebook = self.post_phonebook('valid', valid_body).json()

        result = self.get_phonebook('valid', phonebook['id'])
        assert_that(result.status_code, equal_to(200))
        assert_that(result.json(), equal_to(phonebook))

    def test_all(self):
        tenant_1, tenant_2 = 'default', 'malicious'
        phonebook_1_body = {'name': 'integration',
                            'description': 'The integration test phonebook'}
        phonebook_1 = self.post_phonebook(tenant_1, phonebook_1_body).json()
        assert_that(
            self.get_phonebook(tenant_1, phonebook_1['id']).json(),
            equal_to(phonebook_1),
        )

        expected = dict(phonebook_1_body)
        expected['id'] = ANY
        assert_that(phonebook_1, equal_to(expected))

        phonebook_2 = self.post_phonebook(tenant_1, {'name': 'second'}).json()
        phonebook_2_modified = self.put_phonebook(tenant_1, phonebook_2['id'],
                                                  {'name': 'second',
                                                   'description': 'The second phonebook'})

        assert_that(self.list_phonebooks(tenant_1), contains_inanyorder(phonebook_1, phonebook_2_modified))

        self.delete_phonebook(tenant_2, phonebook_2['id'])
        assert_that(self.list_phonebooks(tenant_1), contains_inanyorder(phonebook_1, phonebook_2_modified))

        self.delete_phonebook(tenant_1, phonebook_2['id'])
        assert_that(self.list_phonebooks(tenant_1), contains_inanyorder(phonebook_1))

        alice = self.post_phonebook_contact(tenant_1, phonebook_1['id'], {'firstname': 'alice'})
        assert_that(self.get_phonebook_contact(tenant_1, phonebook_1['id'], alice['id']),
                    equal_to(alice))
        bob = self.post_phonebook_contact(tenant_1, phonebook_1['id'], {'firstname': 'bob'})
        bob_modified = self.put_phonebook_contact(tenant_1, phonebook_1['id'], bob['id'],
                                                  {'firstname': 'bob',
                                                   'lastname': 'Bibeau'})
        assert_that(self.list_phonebook_contacts(tenant_1, phonebook_1['id']),
                    contains_inanyorder(alice, bob_modified))
