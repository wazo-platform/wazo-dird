# Copyright (C) 2016 Avencall
# SPDX-License-Identifier: GPL-3.0+

from mock import ANY
from hamcrest import assert_that, contains_inanyorder, equal_to

from .base_dird_integration_test import BaseDirdIntegrationTest


class TestPhonebookCRUD(BaseDirdIntegrationTest):

    asset = 'phonebook_only'

    def test_all(self):
        tenant_1, tenant_2 = 'default', 'malicious'
        phonebook_1_body = {'name': 'integration',
                            'description': 'The integration test phonebook'}
        phonebook_1 = self.post_phonebook(tenant_1, phonebook_1_body)
        assert_that(self.get_phonebook(tenant_1, phonebook_1['id']), equal_to(phonebook_1))

        expected = dict(phonebook_1_body)
        expected['id'] = ANY
        assert_that(phonebook_1, equal_to(expected))

        phonebook_2 = self.post_phonebook(tenant_1, {'name': 'second'})
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
