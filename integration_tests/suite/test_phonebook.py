# Copyright 2016-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import uuid
from unittest.mock import ANY

from hamcrest import (
    assert_that,
    contains,
    contains_inanyorder,
    contains_string,
    equal_to,
    has_entries,
    instance_of,
)

from .helpers.phonebook import BasePhonebookTestCase


def generate_tenant_uuid():
    return str(uuid.uuid4())


def raise_for_status(response):
    response.raise_for_status()
    return response


class TestList(BasePhonebookTestCase):
    def test_unknown_tenant(self):
        invalid, *_ = self.set_tenants('invalid')
        valid_body = {'name': 'foobar'}
        raise_for_status(self.post_phonebook(valid_body, tenant=invalid.uuid)).json()

        self.set_tenants()
        result = self.list_phonebooks(tenant=generate_tenant_uuid())
        assert_that(result.status_code, equal_to(401))

    def test_valid(self):
        valid, *_ = self.set_tenants('valid')
        valid_body = {'name': 'foobar'}
        phonebook_1 = raise_for_status(
            self.post_phonebook(valid_body, tenant=valid.uuid)
        ).json()

        result = self.list_phonebooks(tenant=valid.uuid)
        assert_that(
            result.json(),
            has_entries(items=contains_inanyorder(has_entries(**phonebook_1)), total=1),
        )

    def test_pagination(self):
        pagination, *_ = self.set_tenants('pagination')

        valid_body_1 = {'name': 'a', 'description': 'c'}
        valid_body_2 = {'name': 'b', 'description': 'b'}
        valid_body_3 = {'name': 'c', 'description': 'a'}
        phonebook_1 = raise_for_status(
            self.post_phonebook(valid_body_1, tenant=pagination.uuid)
        ).json()
        phonebook_2 = raise_for_status(
            self.post_phonebook(valid_body_2, tenant=pagination.uuid)
        ).json()
        phonebook_3 = raise_for_status(
            self.post_phonebook(valid_body_3, tenant=pagination.uuid)
        ).json()

        def assert_matches(result, *phonebooks):
            assert_that(
                result.json(),
                has_entries(
                    items=contains(
                        *[has_entries(**phonebook) for phonebook in phonebooks]
                    ),
                    total=3,
                ),
            )

        result = self.list_phonebooks(
            order='name', direction='asc', tenant=pagination.uuid
        )
        assert_matches(result, phonebook_1, phonebook_2, phonebook_3)

        result = self.list_phonebooks(
            order='name', direction='desc', tenant=pagination.uuid
        )
        assert_matches(result, phonebook_3, phonebook_2, phonebook_1)

        result = self.list_phonebooks(order='description', tenant=pagination.uuid)
        assert_matches(result, phonebook_3, phonebook_2, phonebook_1)

        result = self.list_phonebooks(limit=2, tenant=pagination.uuid)
        assert_matches(result, phonebook_1, phonebook_2)

        result = self.list_phonebooks(offset=1, tenant=pagination.uuid)
        assert_matches(result, phonebook_2, phonebook_3)

        result = self.list_phonebooks(limit=1, offset=1, tenant=pagination.uuid)
        assert_matches(result, phonebook_2)

        invalid_limit_offset = [-1, True, False, 'foobar', 3.14]
        for value in invalid_limit_offset:
            result = self.list_phonebooks(limit=value, tenant=pagination.uuid)
            assert_that(result.status_code, equal_to(400), value)

            result = self.list_phonebooks(offset=value, tenant=pagination.uuid)
            assert_that(result.status_code, equal_to(400), value)

        invalid_directions = [0, 'foobar', True, False, 3.14]
        for value in invalid_directions:
            result = self.list_phonebooks(direction=value, tenant=pagination.uuid)
            assert_that(result.status_code, equal_to(400), value)

        invalid_orders = [0, True, False, 3.14]
        for value in invalid_orders:
            result = self.list_phonebooks(order=value, tenant=pagination.uuid)
            assert_that(result.status_code, equal_to(400), value)


class TestPost(BasePhonebookTestCase):
    def test_unknown_tenant(self):
        self.set_tenants()
        valid_body = {'name': 'foobar'}
        result = self.post_phonebook(valid_body, tenant=generate_tenant_uuid())
        assert_that(result.status_code, equal_to(401))

    def test_valid(self):
        valid, *_ = self.set_tenants('valid')
        valid_body = {'name': 'foobar'}
        result = self.post_phonebook(valid_body, tenant=valid.uuid)
        assert_that(result.status_code, equal_to(201))
        assert_that(result.json(), has_entries(id=ANY, name='foobar', description=None))

        result = self.post_phonebook(valid_body, tenant=valid.uuid)
        assert_that(result.status_code, equal_to(409))

    def test_invalid_bodies(self):
        invalid, *_ = self.set_tenants('invalid')
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
            result = self.post_phonebook(body, tenant=invalid.uuid)
            assert_that(result.status_code, equal_to(400), body)


class TestGet(BasePhonebookTestCase):
    def test_unknown_tenant(self):
        valid, *_ = self.set_tenants('valid')

        valid_body = {'name': 'foobar'}
        phonebook = raise_for_status(
            self.post_phonebook(valid_body, tenant=valid.uuid)
        ).json()

        self.set_tenants()
        result = self.get_phonebook(phonebook['uuid'], tenant=generate_tenant_uuid())
        assert_that(result.status_code, equal_to(401))

    def test_valid(self):
        valid, *_ = self.set_tenants('valid')

        valid_body = {'name': 'foobaz'}
        phonebook = raise_for_status(
            self.post_phonebook(valid_body, tenant=valid.uuid)
        ).json()

        result = self.get_phonebook(phonebook['uuid'], tenant=valid.uuid)
        assert_that(result.status_code, equal_to(200))
        assert_that(result.json(), equal_to(phonebook))

    def test_unknown_phonebook(self):
        valid, *_ = self.set_tenants('valid')

        valid_body = {'name': 'delete me'}
        phonebook = raise_for_status(
            self.post_phonebook(valid_body, tenant=valid.uuid)
        ).json()

        other, *_ = self.set_tenants('other')
        result = self.get_phonebook('other', phonebook['uuid'], tenant=other.uuid)
        assert_that(result.status_code, equal_to(404))

        valid, *_ = self.set_tenants('valid')
        raise_for_status(self.delete_phonebook(phonebook['uuid'], tenant=valid.uuid))
        result = self.get_phonebook(phonebook['uuid'], tenant=valid.uuid)
        assert_that(result.status_code, equal_to(404))


class TestDelete(BasePhonebookTestCase):
    def test_unknown_tenant(self):
        invalid, *_ = self.set_tenants('invalid')
        valid_body = {'name': 'foobar'}
        phonebook = raise_for_status(
            self.post_phonebook(valid_body, tenant=invalid.uuid)
        ).json()

        self.set_tenants()
        result = self.delete_phonebook(phonebook['uuid'], tenant=generate_tenant_uuid())
        assert_that(result.status_code, equal_to(401))

    def test_valid(self):
        valid, *_ = self.set_tenants('valid')
        valid_body = {'name': 'foobaz'}
        phonebook = raise_for_status(
            self.post_phonebook(valid_body, tenant=valid.uuid)
        ).json()
        result = self.delete_phonebook(phonebook['uuid'], tenant=valid.uuid)
        assert_that(result.status_code, equal_to(204))

    def test_unknown_phonebook(self):
        valid, *_ = self.set_tenants('valid')
        valid_body = {'name': 'foobaz'}
        phonebook = raise_for_status(
            self.post_phonebook(valid_body, tenant=valid.uuid)
        ).json()

        other, *_ = self.set_tenants('other')
        result = self.delete_phonebook('other', phonebook['uuid'], tenant=other.uuid)
        assert_that(result.status_code, equal_to(404))

        valid, *_ = self.set_tenants('valid')
        result = self.delete_phonebook(phonebook['uuid'], tenant=valid.uuid)
        assert_that(result.status_code, equal_to(204))

        result = self.delete_phonebook(phonebook['uuid'], tenant=valid.uuid)
        assert_that(result.status_code, equal_to(404))


class TestPut(BasePhonebookTestCase):
    def test_unknown_tenant(self):
        invalid, *_ = self.set_tenants('invalid')
        valid_body = {'name': 'foobar'}
        phonebook = raise_for_status(
            self.post_phonebook(valid_body, tenant=invalid.uuid)
        ).json()

        self.set_tenants()
        result = self.put_phonebook(
            phonebook['uuid'], {'name': 'new'}, tenant=generate_tenant_uuid()
        )
        assert_that(result.status_code, equal_to(401))

    def test_valid(self):
        valid, *_ = self.set_tenants('valid')
        valid_body = {'name': 'foobaz'}
        phonebook = raise_for_status(
            self.post_phonebook(valid_body, tenant=valid.uuid)
        ).json()

        result = self.put_phonebook(
            phonebook['uuid'], {'name': 'new'}, tenant=valid.uuid
        )
        assert_that(result.status_code, equal_to(200))

    def test_unknown_phonebook(self):
        valid, *_ = self.set_tenants('valid')
        valid_body = {'name': 'delete me'}
        phonebook = raise_for_status(
            self.post_phonebook(valid_body, tenant=valid.uuid)
        ).json()

        other, *_ = self.set_tenants('other')
        result = self.put_phonebook(
            phonebook['uuid'], {'name': 'updated'}, tenant=other.uuid
        )
        assert_that(result.status_code, equal_to(404))

        self.delete_phonebook(phonebook['uuid'], tenant=valid.uuid)
        result = self.put_phonebook(
            phonebook['uuid'], {'name': 'updated'}, tenant=valid.uuid
        )
        assert_that(result.status_code, equal_to(401))

    def test_invalid_bodies(self):
        invalid, *_ = self.set_tenants('invalid')
        valid_body = {'name': 'update me'}
        phonebook = raise_for_status(
            self.post_phonebook(valid_body, tenant=invalid.uuid)
        ).json()
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
            result = self.put_phonebook(phonebook['uuid'], body, tenant=invalid.uuid)
            assert_that(result.status_code, equal_to(400), body)

    def test_duplicated(self):
        invalid, *_ = self.set_tenants('invalid')
        valid_body = {'name': 'duplicate me'}
        raise_for_status(self.post_phonebook(valid_body, tenant=invalid.uuid)).json()

        valid_body = {'name': 'duplicate me NOT'}
        phonebook = raise_for_status(
            self.post_phonebook(valid_body, tenant=invalid.uuid)
        ).json()

        result = self.put_phonebook(
            phonebook['uuid'], {'name': 'duplicate me'}, tenant=invalid.uuid
        )
        assert_that(result.status_code, equal_to(409))


class _BasePhonebookContactTestCase(BasePhonebookTestCase):
    def setUp(self):
        super().setUp()
        self.tenant_1, *_ = self.set_tenants('valid')
        self.phonebook_1 = raise_for_status(
            self.post_phonebook({'name': 'one'}, tenant=self.tenant_1.uuid)
        ).json()

        self.tenant_2, *_ = self.set_tenants('other')
        self.phonebook_2 = raise_for_status(
            self.post_phonebook({'name': 'two'}, tenant=self.tenant_2.uuid)
        ).json()

    def tearDown(self):
        self.set_tenants(self.tenant_1.name)
        raise_for_status(
            self.delete_phonebook(self.phonebook_1['uuid'], tenant=self.tenant_1.uuid)
        )

        self.set_tenants(self.tenant_2.name)
        raise_for_status(
            self.delete_phonebook(self.phonebook_2['uuid'], tenant=self.tenant_2.uuid)
        )
        super().tearDown()


class TestContactDelete(_BasePhonebookContactTestCase):
    def setUp(self):
        super().setUp()
        self.set_tenants(self.tenant_1.name)
        self.contact = raise_for_status(
            self.post_phonebook_contact(
                self.phonebook_1['uuid'],
                {'firstname': 'Alice'},
                tenant=self.tenant_1.uuid,
            )
        ).json()
        self.contact_uuid = self.contact['id']

    def _delete(self, tenant, phonebook_uuid, contact_uuid):
        return self.delete_phonebook_contact(
            phonebook_uuid, contact_uuid, tenant=tenant.uuid
        )

    def test_unknown_tenant_phonebook_or_contact(self):
        self.set_tenants(self.tenant_2.name)
        res = self._delete(self.tenant_2, self.phonebook_1['uuid'], self.contact_uuid)
        assert_that(res.status_code, equal_to(404), 'unknown tenant')

        res = self._delete(self.tenant_1, self.phonebook_1['uuid'], self.contact_uuid)
        assert_that(res.status_code, equal_to(401), 'unknown tenant')

        self.set_tenants(self.tenant_1.name)
        res = self._delete(self.tenant_1, self.phonebook_2['uuid'], self.contact_uuid)
        assert_that(res.status_code, equal_to(404), 'unknown phonebook')

        self._delete(self.tenant_1, self.phonebook_1['uuid'], self.contact_uuid)
        res = self._delete(self.tenant_1, self.phonebook_1['uuid'], self.contact_uuid)
        assert_that(res.status_code, equal_to(404), 'unknown contact')

    def test_delete(self):
        self.set_tenants(self.tenant_1.name)
        res = self._delete(self.tenant_1, self.phonebook_1['uuid'], self.contact_uuid)
        assert_that(res.status_code, equal_to(204))


class TestContactGet(_BasePhonebookContactTestCase):
    def setUp(self):
        super().setUp()
        self.set_tenants(self.tenant_1.name)
        self.contact = raise_for_status(
            self.post_phonebook_contact(
                self.phonebook_1['uuid'],
                {'firstname': 'Alice'},
                tenant=self.tenant_1.uuid,
            )
        ).json()
        self.contact_uuid = self.contact['id']

    def _get(self, tenant, phonebook_id, contact_uuid):
        return self.get_phonebook_contact(
            phonebook_id, contact_uuid, tenant=tenant.uuid
        )

    def test_unknown_tenant_phonebook_or_contact(self):
        self.set_tenants(self.tenant_2.name)
        res = self._get(self.tenant_2, self.phonebook_1['uuid'], self.contact_uuid)
        assert_that(res.status_code, equal_to(404), 'unknown tenant')

        res = self._get(self.tenant_1, self.phonebook_1['uuid'], self.contact_uuid)
        assert_that(res.status_code, equal_to(401), 'unknown tenant')

        self.set_tenants(self.tenant_1.name)
        res = self._get(self.tenant_1, self.phonebook_2['uuid'], self.contact_uuid)
        assert_that(res.status_code, equal_to(404), 'unknown phonebook')

        raise_for_status(
            self.delete_phonebook_contact(
                self.phonebook_1['uuid'], self.contact_uuid, tenant=self.tenant_1.uuid
            )
        )
        res = self._get(self.tenant_1, self.phonebook_1['uuid'], self.contact_uuid)
        assert_that(res.status_code, equal_to(404), 'unknown contact')

    def test_get(self):
        self.set_tenants(self.tenant_1.name)
        res = self._get(self.tenant_1, self.phonebook_1['uuid'], self.contact_uuid)
        assert_that(res.json(), equal_to(self.contact))


class TestContactList(_BasePhonebookContactTestCase):
    def test_unknown_tenant_or_phonebook(self):
        self.set_tenants(self.tenant_2.name)
        result = self.list_phonebook_contacts(
            self.phonebook_1['uuid'], tenant=self.tenant_2.uuid
        )
        assert_that(result.status_code, equal_to(404))

        result = self.list_phonebook_contacts(
            self.phonebook_1['uuid'], tenant=self.tenant_1.uuid
        )
        assert_that(result.status_code, equal_to(401))

    def test_pagination(self):
        self.set_tenants(self.tenant_1.name)
        phonebook_uuid = self.phonebook_1['uuid']

        body_1 = {'firstname': 'a', 'lastname': 'c'}
        body_2 = {'firstname': 'b', 'lastname': 'b'}
        body_3 = {'firstname': 'c', 'lastname': 'a'}
        contact_1 = raise_for_status(
            self.post_phonebook_contact(
                phonebook_uuid, body_1, tenant=self.tenant_1.uuid
            )
        ).json()
        contact_2 = raise_for_status(
            self.post_phonebook_contact(
                phonebook_uuid, body_2, tenant=self.tenant_1.uuid
            )
        ).json()
        contact_3 = raise_for_status(
            self.post_phonebook_contact(
                phonebook_uuid, body_3, tenant=self.tenant_1.uuid
            )
        ).json()

        def assert_matches(result, *contacts):
            raise_for_status(result)
            assert_that(
                result.json(),
                has_entries(
                    items=contains(*[has_entries(**contact) for contact in contacts]),
                    total=3,
                ),
            )

        result = self.list_phonebook_contacts(
            phonebook_uuid,
            order='firstname',
            direction='asc',
            tenant=self.tenant_1.uuid,
        )
        assert_matches(result, contact_1, contact_2, contact_3)

        result = self.list_phonebook_contacts(
            phonebook_uuid,
            order='firstname',
            direction='desc',
            tenant=self.tenant_1.uuid,
        )
        assert_matches(result, contact_3, contact_2, contact_1)

        result = self.list_phonebook_contacts(
            phonebook_uuid, order='lastname', tenant=self.tenant_1.uuid
        )
        assert_matches(result, contact_3, contact_2, contact_1)

        result = self.list_phonebook_contacts(
            phonebook_uuid, order='firstname', limit=2, tenant=self.tenant_1.uuid
        )
        assert_matches(result, contact_1, contact_2)

        result = self.list_phonebook_contacts(
            phonebook_uuid, order='firstname', offset=1, tenant=self.tenant_1.uuid
        )
        assert_matches(result, contact_2, contact_3)

        result = self.list_phonebook_contacts(
            phonebook_uuid,
            order='firstname',
            limit=1,
            offset=1,
            tenant=self.tenant_1.uuid,
        )
        assert_matches(result, contact_2)

        invalid_limit_offset = [-1, True, False, 'foobar', 3.14]
        for value in invalid_limit_offset:
            result = self.list_phonebook_contacts(
                phonebook_uuid, limit=value, tenant=self.tenant_1.uuid
            )
            assert_that(result.status_code, equal_to(400), value)

            result = self.list_phonebook_contacts(
                phonebook_uuid, offset=value, tenant=self.tenant_1.uuid
            )
            assert_that(result.status_code, equal_to(400), value)

        invalid_directions = [0, 'foobar', True, False, 3.14]
        for value in invalid_directions:
            result = self.list_phonebook_contacts(
                phonebook_uuid, direction=value, tenant=self.tenant_1.uuid
            )
            assert_that(result.status_code, equal_to(400), value)


class TestContactPost(_BasePhonebookContactTestCase):
    def test_unknown_tenant_or_phonebook(self):
        body = {'firstname': 'Alice'}

        self.set_tenants(self.tenant_2.name)
        result = self.post_phonebook_contact(
            self.phonebook_1['uuid'], body, tenant=self.tenant_2.uuid
        )
        assert_that(result.status_code, equal_to(404))

        result = self.post_phonebook_contact(
            self.phonebook_1['uuid'], body, tenant=self.tenant_1.uuid
        )
        assert_that(result.status_code, equal_to(401))

    def test_duplicates(self):
        body = {'firstname': 'Alice'}

        self.set_tenants(self.tenant_1.name)
        raise_for_status(
            self.post_phonebook_contact(
                self.phonebook_1['uuid'], body, tenant=self.tenant_1.uuid
            )
        )
        result = self.post_phonebook_contact(
            self.phonebook_1['uuid'], body, tenant=self.tenant_1.uuid
        )
        assert_that(result.status_code, equal_to(409))

        self.set_tenants(self.tenant_2.name)
        result = self.post_phonebook_contact(
            self.phonebook_2['uuid'], body, tenant=self.tenant_2.uuid
        )
        assert_that(result.status_code, equal_to(201))


class TestContactPut(_BasePhonebookContactTestCase):
    def setUp(self):
        super().setUp()
        self.set_tenants(self.tenant_1.name)
        self.contact = raise_for_status(
            self.post_phonebook_contact(
                self.phonebook_1['uuid'],
                {'firstname': 'Alice'},
                tenant=self.tenant_1.uuid,
            )
        ).json()
        self.contact_uuid = self.contact['id']

    def _put(self, tenant, phonebook_id, contact_uuid, body):
        return self.put_phonebook_contact(
            phonebook_id, contact_uuid, body, tenant=tenant.uuid
        )

    def test_unknown_tenant_phonebook_or_contact(self):
        body = {'firstname': 'Bob'}

        self.set_tenants(self.tenant_2.name)
        res = self._put(
            self.tenant_2, self.phonebook_1['uuid'], self.contact_uuid, body
        )
        assert_that(res.status_code, equal_to(404), 'unknown tenant')

        res = self._put(
            self.tenant_1, self.phonebook_1['uuid'], self.contact_uuid, body
        )
        assert_that(res.status_code, equal_to(401), 'unknown tenant')

        self.set_tenants(self.tenant_1.name)
        res = self._put(
            self.tenant_1, self.phonebook_2['uuid'], self.contact_uuid, body
        )
        assert_that(res.status_code, equal_to(404), 'unknown phonebook')

        raise_for_status(
            self.delete_phonebook_contact(
                self.phonebook_1['uuid'], self.contact_uuid, tenant=self.tenant_1.uuid
            )
        )
        res = self._put(
            self.tenant_1, self.phonebook_1['uuid'], self.contact_uuid, body
        )
        assert_that(res.status_code, equal_to(404), 'unknown contact')

    def test_put(self):
        body = {'firstname': 'Bob'}

        self.set_tenants(self.tenant_1.name)
        res = self._put(
            self.tenant_1, self.phonebook_1['uuid'], self.contact_uuid, body
        )
        assert_that(res.json(), has_entries(id=self.contact_uuid, firstname='Bob'))


class TestContactImport(_BasePhonebookContactTestCase):
    def setUp(self):
        super().setUp()
        self.body = '''\
firstname,lastname
Alice,A
Bob,B
'''

    def import_(self, tenant, phonebook_uuid, body):
        return self.import_phonebook_contact(phonebook_uuid, body, tenant=tenant.uuid)

    def test_unknown_tenant_or_phonebook(self):
        self.set_tenants(self.tenant_2.name)
        result = self.import_(self.tenant_2, self.phonebook_1['uuid'], self.body)
        assert_that(result.status_code, equal_to(404))

        result = self.import_(self.tenant_1, self.phonebook_1['uuid'], self.body)
        assert_that(result.status_code, equal_to(401))

    def test_post(self):
        self.set_tenants(self.tenant_1.name)
        result = self.import_(self.tenant_1, self.phonebook_1['uuid'], self.body)
        assert_that(result.status_code, equal_to(200))
        assert_that(
            self.list_phonebook_contacts(
                self.phonebook_1['uuid'], tenant=self.tenant_1.uuid
            ).json(),
            has_entries(
                items=contains_inanyorder(
                    has_entries(firstname='Alice', lastname='A'),
                    has_entries(firstname='Bob', lastname='B'),
                ),
                total=2,
            ),
        )

    def test_post_with_invalid_body(self):
        self.set_tenants(self.tenant_1.name)

        bodies = [
            '',
            'invalid',
            'invalid\n',
        ]

        for body in bodies:
            with self.subTest(body=body):
                result = self.import_(self.tenant_1, self.phonebook_1['uuid'], body)
                assert_that(result.status_code, equal_to(400))

    def test_post_with_invalid_entries(self):
        self.set_tenants(self.tenant_1.name)
        body = '\n'.join(
            [
                'firstname,lastname',
                'Alice,A',
                ',,,',
                'Bob,',
            ]
        )
        result = self.import_(self.tenant_1, self.phonebook_1['uuid'], body)
        assert_that(result.status_code, equal_to(200))
        assert_that(
            result.json(),
            has_entries(
                created=contains_inanyorder(
                    has_entries(firstname='Alice', lastname='A'),
                    has_entries(firstname='Bob', lastname=''),
                ),
                failed=contains_inanyorder(
                    has_entries(
                        contact=has_entries(firstname='', lastname='', null=['', '']),
                        message=contains_string('null key'),
                        details=has_entries(entry_index=instance_of(int)),
                    ),
                ),
            ),
        )

        assert_that(
            self.list_phonebook_contacts(
                self.phonebook_1['uuid'], tenant=self.tenant_1.uuid
            ).json(),
            has_entries(
                items=contains_inanyorder(
                    has_entries(firstname='Alice', lastname='A'),
                    has_entries(firstname='Bob', lastname=''),
                ),
                total=2,
            ),
        )

    def test_post_with_duplicates(self):
        self.set_tenants(self.tenant_1.name)
        result = self.import_(
            self.tenant_1,
            self.phonebook_1['uuid'],
            '\n'.join(['firstname,lastname', 'Alice,A', 'Alice,A', 'Bob,B']),
        )
        assert_that(result.status_code, equal_to(200))
        assert_that(
            result.json(),
            has_entries(
                created=contains_inanyorder(
                    has_entries(firstname='Alice', lastname='A'),
                    has_entries(firstname='Bob', lastname='B'),
                ),
                failed=contains_inanyorder(
                    has_entries(
                        contact=has_entries(firstname='Alice', lastname='A'),
                        message=contains_string('duplicate'),
                    ),
                ),
            ),
        )
