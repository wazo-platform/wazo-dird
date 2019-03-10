# Copyright 2016-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from mock import ANY
from hamcrest import (
    assert_that,
    contains,
    contains_inanyorder,
    equal_to,
    has_entries,
)
from .helpers.base import BasePhonebookTestCase


class TestList(BasePhonebookTestCase):

    def test_unknown_tenant(self):
        self.set_tenants('invalid')
        valid_body = {'name': 'foobar'}
        self.post_phonebook('invalid', valid_body).json()

        self.set_tenants()
        result = self.list_phonebooks('invalid')
        assert_that(result.status_code, equal_to(404))

    def test_valid(self):
        self.set_tenants('valid')
        valid_body = {'name': 'foobar'}
        phonebook_1 = self.post_phonebook('valid', valid_body).json()

        result = self.list_phonebooks('valid')
        assert_that(
            result.json(),
            has_entries(
                items=contains_inanyorder(
                    has_entries(**phonebook_1),
                ),
                total=1,
            )
        )

    def test_pagination(self):
        self.set_tenants('pagination')

        valid_body_1 = {'name': 'a', 'description': 'c'}
        valid_body_2 = {'name': 'b', 'description': 'b'}
        valid_body_3 = {'name': 'c', 'description': 'a'}
        phonebook_1 = self.post_phonebook('pagination', valid_body_1).json()
        phonebook_2 = self.post_phonebook('pagination', valid_body_2).json()
        phonebook_3 = self.post_phonebook('pagination', valid_body_3).json()

        def assert_matches(result, *phonebooks):
            assert_that(
                result.json(),
                has_entries(
                    items=contains(
                        *[has_entries(**phonebook) for phonebook in phonebooks]
                    ),
                    total=3,
                )
            )

        result = self.list_phonebooks('pagination', order='name', direction='asc')
        assert_matches(result, phonebook_1, phonebook_2, phonebook_3)

        result = self.list_phonebooks('pagination', order='name', direction='desc')
        assert_matches(result, phonebook_3, phonebook_2, phonebook_1)

        result = self.list_phonebooks('pagination', order='description')
        assert_matches(result, phonebook_3, phonebook_2, phonebook_1)

        result = self.list_phonebooks('pagination', limit=2)
        assert_matches(result, phonebook_1, phonebook_2)

        result = self.list_phonebooks('pagination', offset=1)
        assert_matches(result, phonebook_2, phonebook_3)

        result = self.list_phonebooks('pagination', limit=1, offset=1)
        assert_matches(result, phonebook_2)

        invalid_limit_offset = [-1, True, False, 'foobar', 3.14]
        for value in invalid_limit_offset:
            result = self.list_phonebooks('pagination', limit=value)
            assert_that(result.status_code, equal_to(400), value)

            result = self.list_phonebooks('pagination', offset=value)
            assert_that(result.status_code, equal_to(400), value)

        invalid_directions = [0, 'foobar', True, False, 3.14]
        for value in invalid_directions:
            result = self.list_phonebooks('pagination', direction=value)
            assert_that(result.status_code, equal_to(400), value)

        invalid_orders = [0, True, False, 3.14]
        for value in invalid_orders:
            result = self.list_phonebooks('pagination', order=value)
            assert_that(result.status_code, equal_to(400), value)


class TestPost(BasePhonebookTestCase):

    def test_unknown_tenant(self):
        self.set_tenants()
        valid_body = {'name': 'foobar'}
        result = self.post_phonebook('unknown', valid_body)
        assert_that(result.status_code, equal_to(404))

    def test_valid(self):
        self.set_tenants('valid')
        valid_body = {'name': 'foobar'}
        result = self.post_phonebook('valid', valid_body)
        assert_that(result.status_code, equal_to(201))
        assert_that(
            result.json(),
            has_entries(
                id=ANY,
                name='foobar',
                description=None,
            )
        )

        result = self.post_phonebook('valid', valid_body)
        assert_that(result.status_code, equal_to(409))

    def test_invalid_bodies(self):
        self.set_tenants('invalid')
        bodies = [
            {},
            {'description': 'abc'},
            {'name': 42},
            {'name': ''},
            {'name': True},
            {'name': False},
            {'name': None},
            {'name': 'foo', 'description': 42},
            {'name': 'foo', 'description': True},
            {'name': 'foo', 'description': False},
        ]

        for body in bodies:
            result = self.post_phonebook('invalid', body)
            assert_that(result.status_code, equal_to(400), body)


class TestGet(BasePhonebookTestCase):

    def test_unknown_tenant(self):
        self.set_tenants('valid')
        valid_body = {'name': 'foobar'}
        phonebook = self.post_phonebook('valid', valid_body).json()

        self.set_tenants()
        result = self.get_phonebook('valid', phonebook['id'])
        assert_that(result.status_code, equal_to(404))

    def test_valid(self):
        self.set_tenants('valid')
        valid_body = {'name': 'foobaz'}
        phonebook = self.post_phonebook('valid', valid_body).json()

        result = self.get_phonebook('valid', phonebook['id'])
        assert_that(result.status_code, equal_to(200))
        assert_that(result.json(), equal_to(phonebook))

    def test_unknown_phonebook(self):
        self.set_tenants('valid')
        valid_body = {'name': 'delete me'}
        phonebook = self.post_phonebook('valid', valid_body).json()

        self.set_tenants('other')
        result = self.get_phonebook('other', phonebook['id'])
        assert_that(result.status_code, equal_to(404))

        self.set_tenants('valid')
        self.delete_phonebook('valid', phonebook['id'])
        result = self.get_phonebook('valid', phonebook['id'])
        assert_that(result.status_code, equal_to(404))


class TestDelete(BasePhonebookTestCase):

    def test_unknown_tenant(self):
        self.set_tenants('invalid')
        valid_body = {'name': 'foobar'}
        phonebook = self.post_phonebook('invalid', valid_body).json()

        self.set_tenants()
        result = self.delete_phonebook('invalid', phonebook['id'])
        assert_that(result.status_code, equal_to(404))

    def test_valid(self):
        self.set_tenants('valid')
        valid_body = {'name': 'foobaz'}
        phonebook = self.post_phonebook('valid', valid_body).json()
        result = self.delete_phonebook('valid', phonebook['id'])
        assert_that(result.status_code, equal_to(204))

    def test_unknown_phonebook(self):
        self.set_tenants('valid')
        valid_body = {'name': 'foobaz'}
        phonebook = self.post_phonebook('valid', valid_body).json()

        self.set_tenants('other')
        result = self.delete_phonebook('other', phonebook['id'])
        assert_that(result.status_code, equal_to(404))

        self.set_tenants('valid')
        result = self.delete_phonebook('valid', phonebook['id'])
        assert_that(result.status_code, equal_to(204))

        result = self.delete_phonebook('valid', phonebook['id'])
        assert_that(result.status_code, equal_to(404))


class TestPut(BasePhonebookTestCase):

    def test_unknown_tenant(self):
        self.set_tenants('invalid')
        valid_body = {'name': 'foobar'}
        phonebook = self.post_phonebook('invalid', valid_body).json()

        self.set_tenants()
        result = self.put_phonebook('invalid', phonebook['id'], {'name': 'new'})
        assert_that(result.status_code, equal_to(404))

    def test_valid(self):
        self.set_tenants('valid')
        valid_body = {'name': 'foobaz'}
        phonebook = self.post_phonebook('valid', valid_body).json()

        result = self.put_phonebook('valid', phonebook['id'], {'name': 'new'})
        assert_that(result.status_code, equal_to(200))

    def test_unknown_phonebook(self):
        self.set_tenants('valid')
        valid_body = {'name': 'delete me'}
        phonebook = self.post_phonebook('valid', valid_body).json()

        self.set_tenants('other')
        result = self.put_phonebook('other', phonebook['id'], {'name': 'updated'})
        assert_that(result.status_code, equal_to(404))

        self.delete_phonebook('valid', phonebook['id'])
        result = self.put_phonebook('valid', phonebook['id'], {'name': 'updated'})
        assert_that(result.status_code, equal_to(404))

    def test_invalid_bodies(self):
        self.set_tenants('invalid')
        valid_body = {'name': 'update me'}
        phonebook = self.post_phonebook('invalid', valid_body).json()
        bodies = [
            {},
            {'description': 'abc'},
            {'name': 42},
            {'name': ''},
            {'name': True},
            {'name': False},
            {'name': None},
            {'name': 'foo', 'description': 42},
            {'name': 'foo', 'description': True},
            {'name': 'foo', 'description': False},
        ]

        for body in bodies:
            result = self.put_phonebook('invalid', phonebook['id'], body)
            assert_that(result.status_code, equal_to(400), body)

    def test_duplicated(self):
        self.set_tenants('invalid')
        valid_body = {'name': 'duplicate me'}
        self.post_phonebook('invalid', valid_body).json()

        valid_body = {'name': 'duplicate me NOT'}
        phonebook = self.post_phonebook('invalid', valid_body).json()

        result = self.put_phonebook('invalid', phonebook['id'], {'name': 'duplicate me'})
        assert_that(result.status_code, equal_to(409))


class _BasePhonebookContactTestCase(BasePhonebookTestCase):

    def setUp(self):
        super().setUp()
        self.tenant_1 = 'valid'
        self.set_tenants('valid')
        self.phonebook_1 = self.post_phonebook(self.tenant_1, {'name': 'one'}).json()

        self.tenant_2 = 'other'
        self.set_tenants(self.tenant_2)
        self.phonebook_2 = self.post_phonebook(self.tenant_2, {'name': 'two'}).json()

    def tearDown(self):
        self.set_tenants(self.tenant_1)
        self.delete_phonebook(self.tenant_1, self.phonebook_1['id'])

        self.set_tenants(self.tenant_2)
        self.delete_phonebook(self.tenant_2, self.phonebook_2['id'])
        super().tearDown()


class TestContactDelete(_BasePhonebookContactTestCase):

    def setUp(self):
        super().setUp()
        self.set_tenants(self.tenant_1)
        self.contact = self.post_phonebook_contact(
            self.tenant_1,
            self.phonebook_1['id'],
            {'firstname': 'Alice'},
        ).json()
        self.contact_id = self.contact['id']

    def test_unknown_tenant_phonebook_or_contact(self):
        self.set_tenants(self.tenant_2)
        res = self.delete(self.tenant_2, self.phonebook_1['id'], self.contact_id)
        assert_that(res.status_code, equal_to(404), 'unknown tenant')

        res = self.delete(self.tenant_1, self.phonebook_1['id'], self.contact_id)
        assert_that(res.status_code, equal_to(404), 'unknown tenant')

        self.set_tenants(self.tenant_1)
        res = self.delete(self.tenant_1, self.phonebook_2['id'], self.contact_id)
        assert_that(res.status_code, equal_to(404), 'unknown phonebook')

        self.delete(self.tenant_1, self.phonebook_1['id'], self.contact_id)
        res = self.delete(self.tenant_1, self.phonebook_1['id'], self.contact_id)
        assert_that(res.status_code, equal_to(404), 'unknown contact')

    def test_delete(self):
        self.set_tenants(self.tenant_1)
        res = self.delete(self.tenant_1, self.phonebook_1['id'], self.contact_id)
        assert_that(res.status_code, equal_to(204))

    def delete(self, tenant, phonebook_id, contact_id):
        return self.delete_phonebook_contact(tenant, phonebook_id, contact_id)


class TestContactGet(_BasePhonebookContactTestCase):

    def setUp(self):
        super().setUp()
        self.set_tenants(self.tenant_1)
        self.contact = self.post_phonebook_contact(
            self.tenant_1,
            self.phonebook_1['id'],
            {'firstname': 'Alice'},
        ).json()
        self.contact_id = self.contact['id']

    def test_unknown_tenant_phonebook_or_contact(self):
        self.set_tenants(self.tenant_2)
        res = self._get(self.tenant_2, self.phonebook_1['id'], self.contact_id)
        assert_that(res.status_code, equal_to(404), 'unknown tenant')

        res = self._get(self.tenant_1, self.phonebook_1['id'], self.contact_id)
        assert_that(res.status_code, equal_to(404), 'unknown tenant')

        self.set_tenants(self.tenant_1)
        res = self._get(self.tenant_1, self.phonebook_2['id'], self.contact_id)
        assert_that(res.status_code, equal_to(404), 'unknown phonebook')

        self.delete_phonebook_contact(self.tenant_1, self.phonebook_1['id'], self.contact_id)
        res = self._get(self.tenant_1, self.phonebook_1['id'], self.contact_id)
        assert_that(res.status_code, equal_to(404), 'unknown contact')

    def test_get(self):
        self.set_tenants(self.tenant_1)
        res = self._get(self.tenant_1, self.phonebook_1['id'], self.contact_id)
        assert_that(res.json(), equal_to(self.contact))

    def _get(self, tenant, phonebook_id, contact_id):
        return self.get_phonebook_contact(tenant, phonebook_id, contact_id)


class TestContactList(_BasePhonebookContactTestCase):

    def test_unknown_tenant_or_phonebook(self):
        self.set_tenants(self.tenant_2)
        result = self.list_phonebook_contacts(self.tenant_2, self.phonebook_1['id'])
        assert_that(result.status_code, equal_to(404))

        result = self.list_phonebook_contacts(self.tenant_1, self.phonebook_1['id'])
        assert_that(result.status_code, equal_to(404))

    def test_pagination(self):
        self.set_tenants(self.tenant_1)
        args = (self.tenant_1, self.phonebook_1['id'])

        body_1 = {'firstname': 'a', 'lastname': 'c'}
        body_2 = {'firstname': 'b', 'lastname': 'b'}
        body_3 = {'firstname': 'c', 'lastname': 'a'}
        contact_1 = self.post_phonebook_contact(*args, body_1).json()
        contact_2 = self.post_phonebook_contact(*args, body_2).json()
        contact_3 = self.post_phonebook_contact(*args, body_3).json()

        def assert_matches(result, *contacts):
            assert_that(
                result.json(),
                has_entries(
                    items=contains(
                        *[has_entries(**contact) for contact in contacts]
                    ),
                    total=3,
                )
            )

        result = self.list_phonebook_contacts(*args, order='firstname', direction='asc')
        assert_matches(result, contact_1, contact_2, contact_3)

        result = self.list_phonebook_contacts(*args, order='firstname', direction='desc')
        assert_matches(result, contact_3, contact_2, contact_1)

        result = self.list_phonebook_contacts(*args, order='lastname')
        assert_matches(result, contact_3, contact_2, contact_1)

        result = self.list_phonebook_contacts(*args, order='firstname', limit=2)
        assert_matches(result, contact_1, contact_2)

        result = self.list_phonebook_contacts(*args, order='firstname', offset=1)
        assert_matches(result, contact_2, contact_3)

        result = self.list_phonebook_contacts(*args, order='firstname', limit=1, offset=1)
        assert_matches(result, contact_2)

        invalid_limit_offset = [-1, True, False, 'foobar', 3.14]
        for value in invalid_limit_offset:
            result = self.list_phonebook_contacts(*args, limit=value)
            assert_that(result.status_code, equal_to(400), value)

            result = self.list_phonebook_contacts(*args, offset=value)
            assert_that(result.status_code, equal_to(400), value)

        invalid_directions = [0, 'foobar', True, False, 3.14]
        for value in invalid_directions:
            result = self.list_phonebook_contacts(*args, direction=value)
            assert_that(result.status_code, equal_to(400), value)


class TestContactPost(_BasePhonebookContactTestCase):

    def test_unknown_tenant_or_phonebook(self):
        body = {'firstname': 'Alice'}

        self.set_tenants(self.tenant_2)
        result = self.post_phonebook_contact(self.tenant_2, self.phonebook_1['id'], body)
        assert_that(result.status_code, equal_to(404))

        result = self.post_phonebook_contact(self.tenant_1, self.phonebook_1['id'], body)
        assert_that(result.status_code, equal_to(404))

    def test_duplicates(self):
        body = {'firstname': 'Alice'}

        self.set_tenants(self.tenant_1)
        self.post_phonebook_contact(self.tenant_1, self.phonebook_1['id'], body)
        result = self.post_phonebook_contact(self.tenant_1, self.phonebook_1['id'], body)
        assert_that(result.status_code, equal_to(409))

        self.set_tenants(self.tenant_2)
        result = self.post_phonebook_contact(self.tenant_2, self.phonebook_2['id'], body)
        assert_that(result.status_code, equal_to(201))


class TestContactPut(_BasePhonebookContactTestCase):

    def setUp(self):
        super().setUp()
        self.set_tenants(self.tenant_1)
        self.contact = self.post_phonebook_contact(
            self.tenant_1,
            self.phonebook_1['id'],
            {'firstname': 'Alice'},
        ).json()
        self.contact_id = self.contact['id']

    def test_unknown_tenant_phonebook_or_contact(self):
        body = {'firstname': 'Bob'}

        self.set_tenants(self.tenant_2)
        res = self.put(self.tenant_2, self.phonebook_1['id'], self.contact_id, body)
        assert_that(res.status_code, equal_to(404), 'unknown tenant')

        res = self.put(self.tenant_1, self.phonebook_1['id'], self.contact_id, body)
        assert_that(res.status_code, equal_to(404), 'unknown tenant')

        self.set_tenants(self.tenant_1)
        res = self.put(self.tenant_1, self.phonebook_2['id'], self.contact_id, body)
        assert_that(res.status_code, equal_to(404), 'unknown phonebook')

        self.delete_phonebook_contact(self.tenant_1, self.phonebook_1['id'], self.contact_id)
        res = self.put(self.tenant_1, self.phonebook_1['id'], self.contact_id, body)
        assert_that(res.status_code, equal_to(404), 'unknown contact')

    def test_put(self):
        body = {'firstname': 'Bob'}

        self.set_tenants(self.tenant_1)
        res = self.put(self.tenant_1, self.phonebook_1['id'], self.contact_id, body)
        assert_that(res.json(), has_entries(id=self.contact_id, firstname='Bob'))

    def put(self, tenant, phonebook_id, contact_id, body):
        return self.put_phonebook_contact(tenant, phonebook_id, contact_id, body)


class TestContactImport(_BasePhonebookContactTestCase):

    def setUp(self):
        super().setUp()
        self.body = '''\
firstname,lastname
Alice,A
Bob,B
'''

    def test_unknown_tenant_or_phonebook(self):
        self.set_tenants(self.tenant_2)
        result = self.import_(self.tenant_2, self.phonebook_1['id'], self.body)
        assert_that(result.status_code, equal_to(404))

        result = self.import_(self.tenant_1, self.phonebook_1['id'], self.body)
        assert_that(result.status_code, equal_to(404))

    def test_post(self):
        self.set_tenants(self.tenant_1)
        result = self.import_(self.tenant_1, self.phonebook_1['id'], self.body)
        assert_that(result.status_code, equal_to(200))
        assert_that(
            self.list_phonebook_contacts(self.tenant_1, self.phonebook_1['id']).json(),
            has_entries(
                items=contains_inanyorder(
                    has_entries(firstname='Alice', lastname='A'),
                    has_entries(firstname='Bob', lastname='B'),
                ),
                total=2,
            )
        )

    def import_(self, tenant, phonebook_id, body):
        return self.import_phonebook_contact(tenant, phonebook_id, body)
