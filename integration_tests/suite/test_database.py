# Copyright 2016-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import functools
import unittest
from collections import defaultdict
from contextlib import closing, contextmanager
from typing import Any
from unittest.mock import ANY

from hamcrest import (
    any_of,
    assert_that,
    calling,
    contains,
    contains_inanyorder,
    empty,
    equal_to,
    has_entries,
    has_item,
    has_items,
    not_,
    raises,
)
from sqlalchemy import and_, exc, func
from sqlalchemy.orm import scoped_session
from wazo_test_helpers.hamcrest.uuid_ import uuid_

from wazo_dird import database, exception
from wazo_dird.database.queries import base

from .helpers.base import DBRunningTestCase
from .helpers.fixtures import db as fixtures
from .helpers.utils import new_uuid

Session: scoped_session = None


TENANT_UUID = new_uuid()


def expected(contact):
    result = {'id': ANY}
    result.update(contact)
    return result


def with_user_uuid(f):
    @functools.wraps(f)
    def wrapped(self, *args, **kwargs):
        user_uuid = new_uuid()
        user = database.User(user_uuid=user_uuid, tenant_uuid=TENANT_UUID)
        with closing(Session()) as session:
            tenant = (
                session.query(database.Tenant)
                .filter(database.Tenant.uuid == TENANT_UUID)
                .first()
            )
            if not tenant:
                tenant = database.Tenant(uuid=TENANT_UUID)
                session.add(tenant)
                session.flush()
            session.add(user)
            session.commit()
            result = f(self, user_uuid, *args, **kwargs)
            session.query(database.User).filter(
                database.User.user_uuid == user_uuid
            ).delete()
            session.query(database.Tenant).filter(
                database.Tenant.uuid == TENANT_UUID
            ).delete()
            session.commit()
        return result

    return wrapped


class DBStarter(DBRunningTestCase):
    asset = 'database'


def setup_module():
    global Session
    DBStarter.setUpClass()
    database.Base.metadata.drop_all()
    database.Base.metadata.create_all()
    Session = DBStarter.Session


def teardown_module():
    DBStarter.tearDownClass()


class _BaseTest(unittest.TestCase):
    def setUp(self):
        self.display_crud = database.DisplayCRUD(Session)
        self.profile_crud = database.ProfileCRUD(Session)
        self.source_crud = database.SourceCRUD(Session)

        self._contact_1 = {
            'firtname': 'Finley',
            'lastname': 'Shelley',
            'number': '5555551111',
        }
        self._contact_2 = {
            'firstname': 'Cédric',
            'lastname': 'Ora',
            'number': '5555550001',
        }
        self._contact_3 = {
            'firstname': 'Foo',
            'lastname': 'Bar',
            'number': '5555550001',
        }

    @property
    def contact_1(self):
        return dict(self._contact_1)

    @property
    def contact_2(self):
        return dict(self._contact_2)

    @property
    def contact_3(self):
        return dict(self._contact_3)

    def _insert_personal_contacts(self, user_uuid, *contacts):
        ids = []
        with closing(Session()) as session:
            for contact in contacts:
                hash_ = base.compute_contact_hash(contact)
                dird_contact = database.Contact(user_uuid=user_uuid, hash=hash_)
                session.add(dird_contact)
                session.flush()
                ids.append(dird_contact.uuid)
                for name, value in contact.items():
                    field = database.ContactFields(
                        name=name, value=value, contact_uuid=dird_contact.uuid
                    )
                    session.add(field)
                session.commit()
        return ids

    def _list_contacts(self):
        with closing(Session()) as s:
            contacts: dict[str, dict[str, Any]] = defaultdict(dict)
            for field in s.query(database.ContactFields).all():
                contacts[field.contact_uuid][field.name] = field.value
        return list(contacts.values())


class _BasePhonebookCRUDTest(_BaseTest):
    def setUp(self):
        super().setUp()
        self._crud = database.PhonebookCRUD(Session)

    @contextmanager
    def _new_phonebook(self, tenant_uuid, name, description=None, delete=True):
        body = {'name': name}
        if description:
            body['description'] = description

        phonebook = self._crud.create(tenant_uuid, body)
        yield phonebook
        if delete:
            self._crud.delete(
                [tenant_uuid], database.PhonebookKey(uuid=phonebook['uuid'])
            )


class TestBaseDAO(_BaseTest):
    def test_that_an_unexpected_error_does_not_block_the_current_Session(self):
        dao = base.BaseDAO(Session)

        try:
            with dao.new_session() as s:
                phonebook_1 = database.Phonebook()
                s.add(phonebook_1)
                s.commit()
        except exc.SQLAlchemyError:
            pass
        else:
            self.fail('The context manager should reraise the exception')

        try:
            with dao.new_session() as s:
                phonebook = database.Phonebook(name='bar')
                s.add(phonebook)
        except exc.InvalidRequestError:
            self.fail('Should not raise')


class TestDisplayCRUD(_BaseTest):
    def test_create_no_error(self):
        tenant_uuid = new_uuid()
        name = 'english'
        body = {
            'tenant_uuid': tenant_uuid,
            'name': name,
            'columns': [
                {'field': 'firstname', 'title': 'Firstname'},
                {'field': 'lastname', 'title': 'Lastname', 'default': ''},
                {'field': 'number', 'title': 'Number', 'type': 'number'},
                {
                    'field': 'mobile',
                    'title': 'Mobile',
                    'type': 'number',
                    'number_display': '{firstname} {lastname} (Mobile)',
                },
            ],
        }

        result = self.display_crud.create(**body)
        try:
            assert_that(
                result,
                has_entries(
                    uuid=uuid_(),
                    tenant_uuid=tenant_uuid,
                    name=name,
                    columns=contains(
                        has_entries(field='firstname', title='Firstname'),
                        has_entries(field='lastname', title='Lastname', default=''),
                        has_entries(field='number', title='Number', type='number'),
                        has_entries(
                            field='mobile',
                            title='Mobile',
                            type='number',
                            number_display='{firstname} {lastname} (Mobile)',
                        ),
                    ),
                ),
            )
        finally:
            self.display_crud.delete(None, result['uuid'])

    @fixtures.display()
    def test_get_with_the_right_tenant(self, display):
        result = self.display_crud.get([display['tenant_uuid']], display['uuid'])
        assert_that(result, equal_to(display))

        assert_that(
            calling(self.display_crud.get).with_args(
                [display['tenant_uuid']], new_uuid()
            ),
            raises(exception.NoSuchDisplay),
        )

    @fixtures.display()
    def test_get_with_the_wrong_tenant(self, display):
        assert_that(
            calling(self.display_crud.get).with_args([new_uuid()], display['uuid']),
            raises(exception.NoSuchDisplay),
        )

    @fixtures.display()
    def test_get_with_no_tenant(self, display):
        result = self.display_crud.get(None, display['uuid'])
        assert_that(result, equal_to(display))

        assert_that(
            calling(self.display_crud.get).with_args([], display['uuid']),
            raises(exception.NoSuchDisplay),
        )

    @fixtures.display()
    def test_delete_with_the_right_tenant(self, display):
        assert_that(
            calling(self.display_crud.delete).with_args(
                [display['tenant_uuid']], display['uuid']
            ),
            not_(raises(Exception)),
        )
        assert_that(
            calling(self.display_crud.delete).with_args(
                [display['tenant_uuid']], display['uuid']
            ),
            raises(exception.NoSuchDisplay),
        )

    @fixtures.display()
    def test_delete_with_the_wrong_tenant(self, display):
        assert_that(
            calling(self.display_crud.delete).with_args([new_uuid()], display['uuid']),
            raises(exception.NoSuchDisplay),
        )

    @fixtures.display()
    def test_delete_with_no_tenant(self, display):
        assert_that(
            calling(self.display_crud.delete).with_args(None, display['uuid']),
            not_(raises(exception.NoSuchDisplay)),
        )

        assert_that(
            calling(self.display_crud.delete).with_args([], display['uuid']),
            raises(exception.NoSuchDisplay),
        )


class TestPhonebookCRUDCount(_BasePhonebookCRUDTest):
    def test_count(self):
        tenant_uuid = new_uuid()
        with self._new_phonebook(tenant_uuid, 'a'), self._new_phonebook(
            tenant_uuid, 'b'
        ), self._new_phonebook(tenant_uuid, 'c'):
            result = self._crud.count([tenant_uuid])

        assert_that(result, equal_to(3))

    def test_that_an_unknown_tenant_returns_zero(self):
        result = self._crud.count(['unknown'])

        assert_that(result, equal_to(0))

    def test_that_phonebooks_from_others_are_not_counted(self):
        tenant_uuid = new_uuid()
        with self._new_phonebook(tenant_uuid, 'a'), self._new_phonebook(
            tenant_uuid, 'b'
        ), self._new_phonebook('other', 'c'):
            result = self._crud.count([tenant_uuid])

        assert_that(result, equal_to(2))

    def test_that_only_matching_phonebooks_are_counted(self):
        tenant_uuid = new_uuid()
        with self._new_phonebook(tenant_uuid, 'ab'), self._new_phonebook(
            tenant_uuid, 'bc'
        ), self._new_phonebook(tenant_uuid, 'cd'):
            result = self._crud.count([tenant_uuid], search='b')

        assert_that(result, equal_to(2))


class TestPhonebookCRUDCreate(_BasePhonebookCRUDTest):
    def tearDown(self):
        with closing(Session()) as session:
            for phonebook in session.query(database.Phonebook).all():
                session.delete(phonebook)
            session.commit()
        super().tearDown()

    def test_that_create_creates_a_phonebook_and_a_tenant(self):
        tenant_uuid = new_uuid()
        body = {'name': 'main', 'description': 'The main phonebook for "default"'}

        result = self._crud.create(tenant_uuid, body)

        assert_that(result, has_entries(id=ANY, uuid=ANY, **body))

    def test_that_create_without_name_fails(self):
        tenant_uuid = new_uuid()

        assert_that(
            calling(self._crud.create).with_args(tenant_uuid, None), raises(Exception)
        )
        assert_that(
            calling(self._crud.create).with_args(tenant_uuid, {}), raises(Exception)
        )
        assert_that(
            calling(self._crud.create).with_args(tenant_uuid, {'name': ''}),
            raises(Exception),
        )

    def test_that_create_without_description(self):
        tenant_uuid = new_uuid()
        body = {'name': 'nodesc'}

        result = self._crud.create(tenant_uuid, body)

        assert_that(result, has_entries(id=ANY, uuid=ANY, description=None, **body))

    def test_that_create_with_invalid_fields_raises(self):
        tenant_uuid = new_uuid()
        body = {'name': 'nodesc', 'foo': 'bar'}

        assert_that(
            calling(self._crud.create).with_args(tenant_uuid, body), raises(TypeError)
        )

    def test_that_create_raises_if_two_phonebook_have_the_same_name_and_tenant(self):
        tenant_uuid = new_uuid()
        body = {'name': 'new'}
        self._crud.create(tenant_uuid, body)

        assert_that(
            calling(self._crud.create).with_args(tenant_uuid, body),
            raises(exception.DuplicatedPhonebookException),
        )

    def test_that_duplicate_tenants_are_not_created(self):
        tenant_uuid = new_uuid()

        self._crud.create(tenant_uuid, {'name': 'first'})
        self._crud.create(tenant_uuid, {'name': 'second'})

        with closing(Session()) as session:
            tenant_count = (
                session.query(func.count(database.Tenant.uuid))
                .filter(database.Tenant.uuid == tenant_uuid)
                .scalar()
            )

        assert_that(tenant_count, equal_to(1))


class TestPhonebookCRUDDelete(_BasePhonebookCRUDTest):
    def test_that_delete_removes_the_phonebook(self):
        tenant_uuid = new_uuid()
        with self._new_phonebook(tenant_uuid, 'first', delete=False) as phonebook:
            self._crud.delete(
                [tenant_uuid], database.PhonebookKey(uuid=phonebook['uuid'])
            )

        with closing(Session()) as session:
            phonebook_count = (
                session.query(func.count(database.Phonebook.uuid))
                .filter(database.Phonebook.uuid == phonebook['uuid'])
                .scalar()
            )

        assert_that(phonebook_count, equal_to(0))

    def test_that_deleting_an_unknown_phonebook_raises(self):
        wrong_tenant_uuid = new_uuid()
        assert_that(
            calling(self._crud.delete).with_args(
                [wrong_tenant_uuid], database.PhonebookKey(uuid=new_uuid())
            ),
            raises(exception.NoSuchPhonebook),
        )

    def test_that_deleting_another_tenant_phonebook_is_not_possible(self):
        tenant_uuid_1 = new_uuid()
        tenant_uuid_2 = new_uuid()

        with self._new_phonebook(tenant_uuid_1, 'main') as phonebook:
            assert_that(
                calling(self._crud.delete).with_args(
                    [tenant_uuid_2], database.PhonebookKey(uuid=phonebook['uuid'])
                ),
                raises(exception.NoSuchPhonebook),
            )

    def test_that_tenants_are_not_created_on_delete(self):
        tenant_uuid_1 = new_uuid()
        tenant_uuid_2 = new_uuid()
        with closing(Session()) as session:
            total_tenant_before = session.query(
                func.count(database.Tenant.uuid)
            ).scalar()

        with self._new_phonebook(tenant_uuid_1, 'a') as phonebook:
            try:
                self._crud.delete(
                    [tenant_uuid_2], database.PhonebookKey(uuid=phonebook['uuid'])
                )
            except exception.NoSuchPhonebook:
                pass  # as expected

        with closing(Session()) as session:
            total_tenant_after = session.query(
                func.count(database.Tenant.uuid)
            ).scalar()

        assert_that(total_tenant_before + 1, equal_to(total_tenant_after))


class TestPhonebookCRUDEdit(_BasePhonebookCRUDTest):
    def test_that_edit_changes_the_phonebook(self):
        tenant_uuid = new_uuid()

        with self._new_phonebook(tenant_uuid, 'name') as phonebook:
            new_body = {'name': 'new_name', 'description': 'lol'}
            result = self._crud.edit(
                [tenant_uuid], database.PhonebookKey(uuid=phonebook['uuid']), new_body
            )

        assert_that(
            result, has_entries(id=phonebook['id'], uuid=phonebook['uuid'], **new_body)
        )

    def test_that_invalid_keys_raise_an_exception(self):
        tenant_uuid = new_uuid()

        with self._new_phonebook(tenant_uuid, 'unknown fields') as phonebook:
            new_body = {'foo': 'bar'}

            assert_that(
                calling(self._crud.edit).with_args(
                    [tenant_uuid],
                    database.PhonebookKey(uuid=phonebook['uuid']),
                    new_body,
                ),
                raises(TypeError),
            )

    def test_that_editing_an_unknown_phonebook_raises(self):
        tenant_uuid = new_uuid()

        assert_that(
            calling(self._crud.edit).with_args(
                [tenant_uuid], database.PhonebookKey(uuid=new_uuid()), {'name': 'test'}
            ),
            raises(exception.NoSuchPhonebook),
        )

    def test_that_editing_a_phonebook_from_another_tenant_raises(self):
        tenant_uuid_1 = new_uuid()
        tenant_uuid_2 = new_uuid()
        with self._new_phonebook(
            tenant_uuid_1, 'a'
        ) as phonebook_a, self._new_phonebook(tenant_uuid_2, 'b'):
            assert_that(
                calling(self._crud.edit).with_args(
                    [tenant_uuid_2],
                    database.PhonebookKey(uuid=phonebook_a['uuid']),
                    {'name': 'foo'},
                ),
                raises(exception.NoSuchPhonebook),
            )


class TestPhonebookCRUDGet(_BasePhonebookCRUDTest):
    def test_that_get_returns_the_phonebook(self):
        tenant_uuid = new_uuid()
        with self._new_phonebook(tenant_uuid, 'a') as phonebook:
            result = self._crud.get(
                [tenant_uuid], database.PhonebookKey(uuid=phonebook['uuid'])
            )

        assert_that(result, equal_to(phonebook))

    def test_that_get_with_an_unknown_id_raises(self):
        tenant_uuid = new_uuid()
        assert_that(
            calling(self._crud.get).with_args(
                [tenant_uuid], database.PhonebookKey(id=42)
            ),
            raises(exception.NoSuchPhonebook),
        )

    def test_that_get_with_an_unknown_uuid_raises(self):
        tenant_uuid = new_uuid()
        assert_that(
            calling(self._crud.get).with_args(
                [tenant_uuid], database.PhonebookKey(uuid=new_uuid())
            ),
            raises(exception.NoSuchPhonebook),
        )

    def test_that_get_from_another_tenant_raises(self):
        tenant_uuid_1 = new_uuid()
        tenant_uuid_2 = new_uuid()
        with self._new_phonebook(tenant_uuid_1, 'a') as phonebook:
            assert_that(
                calling(self._crud.get).with_args(
                    [tenant_uuid_2], database.PhonebookKey(uuid=phonebook['uuid'])
                ),
                raises(exception.NoSuchPhonebook),
            )


class TestPhonebookCRUDList(_BasePhonebookCRUDTest):
    def test_that_all_phonebooks_are_listed(self):
        tenant_uuid = new_uuid()
        with self._new_phonebook(tenant_uuid, 'a') as a, self._new_phonebook(
            tenant_uuid, 'b'
        ) as b, self._new_phonebook(tenant_uuid, 'c') as c:
            result = self._crud.list([tenant_uuid])
        assert_that(result, contains_inanyorder(a, b, c))

    def test_that_phonebooks_from_others_are_not_listed(self):
        tenant_uuid = new_uuid()
        with self._new_phonebook(tenant_uuid, 'a') as a, self._new_phonebook(
            tenant_uuid, 'b'
        ) as b, self._new_phonebook('not_t', 'c'):
            result = self._crud.list([tenant_uuid])
        assert_that(result, contains_inanyorder(a, b))

    def test_that_no_phonebooks_returns_an_empty_list(self):
        tenant_uuid = new_uuid()
        result = self._crud.list([tenant_uuid])

        assert_that(result, empty())

    def test_that_phonebooks_can_be_ordered(self):
        tenant_uuid = new_uuid()
        with self._new_phonebook(
            tenant_uuid, 'a', description='z'
        ) as a, self._new_phonebook(
            tenant_uuid, 'b', description='b'
        ) as b, self._new_phonebook(
            tenant_uuid, 'c'
        ) as c:
            result = self._crud.list([tenant_uuid], order='description')
        assert_that(result, contains_inanyorder(b, a, c))

    def test_that_phonebooks_order_with_invalid_field_raises(self):
        tenant_uuid = new_uuid()
        with self._new_phonebook(
            tenant_uuid, 'a', description='z'
        ), self._new_phonebook(tenant_uuid, 'b', description='b'), self._new_phonebook(
            tenant_uuid, 'c'
        ):
            assert_that(
                calling(self._crud.list).with_args([tenant_uuid], order='foo'),
                raises(TypeError),
            )

    def test_that_phonebooks_can_be_ordered_in_any_order(self):
        tenant_uuid = new_uuid()
        with self._new_phonebook(
            tenant_uuid, 'a', description='z'
        ) as a, self._new_phonebook(
            tenant_uuid, 'b', description='b'
        ) as b, self._new_phonebook(
            tenant_uuid, 'c'
        ) as c:
            result = self._crud.list(
                [tenant_uuid], order='description', direction='desc'
            )
        assert_that(result, contains_inanyorder(a, b, c))

    def test_that_phonebooks_can_be_limited(self):
        tenant_uuid = new_uuid()
        with self._new_phonebook(tenant_uuid, 'a') as a, self._new_phonebook(
            tenant_uuid, 'b'
        ) as b, self._new_phonebook(tenant_uuid, 'c'):
            result = self._crud.list([tenant_uuid], limit=2)
        assert_that(result, contains_inanyorder(a, b))

    def test_that_an_offset_can_be_supplied(self):
        tenant_uuid = new_uuid()
        with self._new_phonebook(tenant_uuid, 'a'), self._new_phonebook(
            tenant_uuid, 'b'
        ), self._new_phonebook(tenant_uuid, 'c') as c:
            result = self._crud.list([tenant_uuid], offset=2)
        assert_that(result, contains_inanyorder(c))

    def test_that_list_only_returns_matching_phonebooks(self):
        tenant_uuid = new_uuid()
        with self._new_phonebook(
            tenant_uuid, 'aa', description='foobar'
        ) as a, self._new_phonebook(tenant_uuid, 'bb') as b, self._new_phonebook(
            tenant_uuid, 'cc'
        ):
            result = self._crud.list([tenant_uuid], search='b')

        assert_that(result, contains_inanyorder(a, b))


class _BasePhonebookContactCRUDTest(_BaseTest):
    def setUp(self):
        super().setUp()
        self._tenant_uuid = new_uuid()
        self._crud = database.PhonebookContactCRUD(Session)
        self._phonebook_crud = database.PhonebookCRUD(Session)
        body = {'name': 'main', 'description': 'the integration test phonebook'}
        self._phonebook = self._phonebook_crud.create(self._tenant_uuid, body)
        self._phonebook_id = self._phonebook['id']
        self._phonebook_uuid = self._phonebook['uuid']
        self._body = {'firstname': 'Foo', 'lastname': 'bar', 'number': '5555555555'}

    def tearDown(self):
        self._phonebook_crud.delete(
            [self._tenant_uuid], database.PhonebookKey(uuid=self._phonebook_uuid)
        )
        super().tearDown()


class TestPhonebookContactCRUDCreate(_BasePhonebookContactCRUDTest):
    def test_that_a_phonebook_contact_can_be_created(self):
        result = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            self._body,
        )

        expected = dict(self._body)
        expected['id'] = ANY
        assert_that(result, equal_to(expected))
        assert_that(self._list_contacts(), has_item(expected))

    def test_that_duplicated_contacts_cannot_be_created(self):
        self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            self._body,
        )
        assert_that(
            calling(self._crud.create).with_args(
                [self._tenant_uuid],
                database.PhonebookKey(uuid=self._phonebook_uuid),
                self._body,
            ),
            raises(exception.DuplicatedContactException),
        )

        assert_that(
            calling(self._crud.create).with_args(
                [self._tenant_uuid],
                database.PhonebookKey(id=self._phonebook_id),
                self._body,
            ),
            raises(exception.DuplicatedContactException),
        )

    def test_that_duplicates_can_happen_in_different_phonebooks(self):
        phonebook_2 = self._phonebook_crud.create(self._tenant_uuid, {'name': 'second'})

        contact_1 = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            self._body,
        )
        contact_2 = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=phonebook_2['uuid']),
            self._body,
        )

        assert_that(self._list_contacts(), has_items(contact_1, contact_2))

    def test_that_a_tenant_can_only_create_in_his_phonebook(self):
        wrong_tenant_uuid = new_uuid()
        assert_that(
            calling(self._crud.create).with_args(
                [wrong_tenant_uuid],
                database.PhonebookKey(uuid=self._phonebook_uuid),
                self._body,
            ),
            raises(exception.NoSuchPhonebook),
        )


class TestPhonebookContactImport(_BasePhonebookContactCRUDTest):
    def test_that_I_can_create_many_contacts(self):
        contact_1 = self._new_contact('Foo', 'Bar', '5555551111')
        contact_2 = self._new_contact('Alice', 'AAA', '5555552222')
        contact_3 = self._new_contact('Bob', 'BBB', '5555553333')
        body = [contact_1, contact_2, contact_3]

        created, errors = self._crud.create_many(
            [self._tenant_uuid], database.PhonebookKey(uuid=self._phonebook_uuid), body
        )

        assert_that(
            created,
            contains_inanyorder(
                has_entries(**contact_1),
                has_entries(**contact_2),
                has_entries(**contact_3),
            ),
        )
        assert_that(errors, empty())

        created, errors = self._crud.create_many(
            [self._tenant_uuid], database.PhonebookKey(id=self._phonebook_id), body
        )
        # duplicates are ignored and do not generate errors
        assert_that(errors, empty())
        assert_that(created, empty())

    @staticmethod
    def _new_contact(firstname, lastname, number):
        return {'firstname': firstname, 'lastname': lastname, 'number': number}


class TestPhonebookContactCRUDDelete(_BasePhonebookContactCRUDTest):
    def test_that_deleting_contact_removes_it(self):
        contact = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            self._body,
        )

        self._crud.delete(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            contact['id'],
        )

        assert_that(self._list_contacts(), not_(has_item(contact)))

    def test_that_deleting_with_another_tenant_does_not_work(self):
        contact = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            self._body,
        )

        wrong_tenant_uuid = new_uuid()
        assert_that(
            calling(self._crud.delete).with_args(
                [wrong_tenant_uuid],
                database.PhonebookKey(uuid=self._phonebook_uuid),
                contact['id'],
            ),
            raises(exception.NoSuchPhonebook),
        )
        assert_that(self._list_contacts(), has_item(contact))

    def test_that_deleting_an_unknown_contact_raises(self):
        unknown_contact_uuid = new_uuid()

        assert_that(
            calling(self._crud.delete).with_args(
                [self._tenant_uuid],
                database.PhonebookKey(uuid=self._phonebook_uuid),
                unknown_contact_uuid,
            ),
            raises(exception.NoSuchContact),
        )


class TestPhonebookContactCRUDGet(_BasePhonebookContactCRUDTest):
    def test_that_get_returns_the_contact(self):
        contact = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            self._body,
        )

        result = self._crud.get(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            contact['id'],
        )

        assert_that(result, equal_to(contact))

    def test_that_get_wont_work_with_the_wrong_phonebook_id(self):
        other_phonebook = self._phonebook_crud.create(
            self._tenant_uuid, {'name': 'other'}
        )
        contact = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            self._body,
        )

        assert_that(
            calling(self._crud.get).with_args(
                [self._tenant_uuid],
                database.PhonebookKey(id=other_phonebook['id']),
                contact['id'],
            ),
            raises(exception.NoSuchContact),
        )
        assert_that(
            calling(self._crud.get).with_args(
                [self._tenant_uuid],
                database.PhonebookKey(uuid=other_phonebook['uuid']),
                contact['id'],
            ),
            raises(exception.NoSuchContact),
        )

    def test_that_get_wont_work_with_the_wrong_tenant(self):
        contact = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            self._body,
        )
        wrong_tenant_uuid = new_uuid()

        assert_that(
            calling(self._crud.get).with_args(
                [wrong_tenant_uuid],
                database.PhonebookKey(uuid=self._phonebook_uuid),
                contact['id'],
            ),
            raises(exception.NoSuchPhonebook),
        )


class TestPhonebookContactCRUDEdit(_BasePhonebookContactCRUDTest):
    def test_that_editing_a_contact_works(self):
        contact = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            self._body,
        )

        new_body = {'firstname': 'Foo', 'lastname': 'Bar', 'number': '5551236666'}

        result = self._crud.edit(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            contact['id'],
            new_body,
        )

        expected = dict(new_body)
        expected['id'] = ANY
        assert_that(result, equal_to(expected))
        assert_that(self._list_contacts(), has_item(expected))

    def test_that_the_id_cannot_be_modified(self):
        contact = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            self._body,
        )

        new_body = dict(contact)
        new_body['id'] = new_uuid()

        result = self._crud.edit(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            contact['id'],
            new_body,
        )

        assert_that(result, equal_to(contact))
        assert_that(self._list_contacts(), has_item(contact))
        assert_that(self._list_contacts(), not (has_item(new_body)))

    def test_that_duplicates_cannot_be_created(self):
        self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            {'name': 'Foo'},
        )
        contact_2 = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            {'name': 'Bar'},
        )

        assert_that(
            calling(self._crud.edit).with_args(
                [self._tenant_uuid],
                database.PhonebookKey(uuid=self._phonebook_uuid),
                contact_2['id'],
                {'id': new_uuid(), 'name': 'Foo'},
            ),
            raises(exception.DuplicatedContactException),
        )

    def test_that_the_phonebook_must_match_the_id(self):
        other_phonebook = self._phonebook_crud.create(
            self._tenant_uuid, {'name': 'the other'}
        )
        contact = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            self._body,
        )

        new_body = {'firstname': 'Foo', 'lastname': 'Bar', 'number': '5551236666'}

        other_phonebook_uuid = other_phonebook['uuid']
        assert_that(
            calling(self._crud.edit).with_args(
                [self._tenant_uuid],
                database.PhonebookKey(uuid=other_phonebook_uuid),
                contact['id'],
                new_body,
            ),
            raises(exception.NoSuchContact),
        )

    def test_that_the_tenant_must_match_the_id(self):
        contact = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            self._body,
        )
        wrong_tenant_uuid = new_uuid()

        new_body = {'firstname': 'Foo', 'lastname': 'Bar', 'number': '5551236666'}

        assert_that(
            calling(self._crud.edit).with_args(
                [wrong_tenant_uuid],
                database.PhonebookKey(uuid=self._phonebook_uuid),
                contact['id'],
                new_body,
            ),
            raises(exception.NoSuchPhonebook),
        )


class TestPhonebookContactCRUDList(_BasePhonebookContactCRUDTest):
    def setUp(self):
        super().setUp()
        self._contact_1 = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            {'name': 'one', 'foo': 'bar'},
        )  # type: ignore
        self._contact_2 = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            {'name': 'two', 'foo': 'bar'},
        )  # type: ignore
        self._contact_3 = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            {'name': 'three', 'foo': 'bar'},
        )  # type: ignore

    def test_that_listing_contacts_works(self):
        result = self._crud.list(
            [self._tenant_uuid], database.PhonebookKey(uuid=self._phonebook_uuid)
        )

        assert_that(
            result,
            contains_inanyorder(self._contact_1, self._contact_2, self._contact_3),
        )

    def test_that_only_the_tenant_can_list(self):
        wrong_tenant_uuid = new_uuid()
        assert_that(
            calling(self._crud.list).with_args(
                [wrong_tenant_uuid], database.PhonebookKey(uuid=self._phonebook_uuid)
            ),
            raises(exception.NoSuchPhonebook),
        )

    def test_that_the_list_can_be_filtered(self):
        result = self._crud.list(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            search='o',
        )

        assert_that(result, contains_inanyorder(self._contact_1, self._contact_2))


class TestPhonebookContactCRUDCount(_BasePhonebookContactCRUDTest):
    def setUp(self):
        super().setUp()
        self._contact_1 = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            {'name': 'one', 'foo': 'bar'},
        )
        self._contact_2 = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            {'name': 'two', 'foo': 'bar'},
        )
        self._contact_3 = self._crud.create(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            {'name': 'three', 'foo': 'bar'},
        )

    def test_that_counting_counts(self):
        result = self._crud.count(
            [self._tenant_uuid], database.PhonebookKey(uuid=self._phonebook_uuid)
        )

        assert_that(result, equal_to(3))

        result = self._crud.count(
            [self._tenant_uuid], database.PhonebookKey(id=self._phonebook_id)
        )
        assert_that(result, equal_to(3))

    def test_that_counting_is_filtered(self):
        result = self._crud.count(
            [self._tenant_uuid],
            database.PhonebookKey(uuid=self._phonebook_uuid),
            search='o',
        )

        assert_that(result, equal_to(2))

        result = self._crud.count(
            [self._tenant_uuid],
            database.PhonebookKey(id=self._phonebook_id),
            search='o',
        )

        assert_that(result, equal_to(2))

    def test_that_counting_from_another_tenant_return_0(self):
        assert_that(
            calling(self._crud.count).with_args(
                [new_uuid()], database.PhonebookKey(uuid=self._phonebook_uuid)
            ),
            raises(exception.NoSuchPhonebook),
        )
        assert_that(
            calling(self._crud.count).with_args(
                [new_uuid()], database.PhonebookKey(id=self._phonebook_id)
            ),
            raises(exception.NoSuchPhonebook),
        )


class TestContactCRUD(_BaseTest):
    def setUp(self):
        super().setUp()
        self._crud = database.PersonalContactCRUD(Session)

    def test_that_create_personal_contact_creates_a_contact_and_the_owner(self):
        owner = new_uuid()

        result = self._crud.create_personal_contact(TENANT_UUID, owner, self.contact_1)
        assert_that(result, equal_to(expected(self.contact_1)))

        contact_list = self._crud.list_personal_contacts(owner)
        assert_that(contact_list, contains(expected(self.contact_1)))

    @with_user_uuid
    def test_that_create_personal_contact_creates_with_existing_owner(self, user_uuid):
        result = self._crud.create_personal_contact(
            TENANT_UUID, user_uuid, self.contact_1
        )
        assert_that(result, equal_to(expected(self.contact_1)))

        contact_list = self._crud.list_personal_contacts(user_uuid)
        assert_that(contact_list, contains(expected(self.contact_1)))

    @with_user_uuid
    def test_that_personal_contacts_are_unique(self, user_uuid):
        self._crud.create_personal_contact(TENANT_UUID, user_uuid, self.contact_1)
        assert_that(
            calling(self._crud.create_personal_contact).with_args(
                TENANT_UUID, user_uuid, self.contact_1
            ),
            raises(exception.DuplicatedContactException),
        )

    @with_user_uuid
    def test_that_personal_contacts_remain_unique(self, user_uuid):
        contact_1_uuid = self._crud.create_personal_contact(
            TENANT_UUID, user_uuid, self.contact_1
        )['id']
        self._crud.create_personal_contact(TENANT_UUID, user_uuid, self.contact_2)['id']

        assert_that(
            calling(self._crud.edit_personal_contact).with_args(
                TENANT_UUID, user_uuid, contact_1_uuid, self.contact_2
            ),
            raises(exception.DuplicatedContactException),
        )
        contact_list = self._crud.list_personal_contacts(user_uuid)
        assert_that(
            contact_list,
            contains_inanyorder(expected(self.contact_1), expected(self.contact_2)),
        )

    @with_user_uuid
    @with_user_uuid
    def test_that_personal_contacts_can_be_duplicated_between_users(
        self, user_uuid_1, user_uuid_2
    ):
        contact_1_uuid = self._crud.create_personal_contact(
            TENANT_UUID, user_uuid_1, self.contact_1
        )['id']
        contact_2_uuid = self._crud.create_personal_contact(
            TENANT_UUID, user_uuid_2, self.contact_1
        )['id']

        assert_that(contact_1_uuid, not_(equal_to(contact_2_uuid)))

    @with_user_uuid
    def test_get_personal_contact(self, user_uuid):
        contact_uuid, _, __ = self._insert_personal_contacts(
            user_uuid, self.contact_1, self.contact_2, self.contact_3
        )

        result = self._crud.get_personal_contact(user_uuid, contact_uuid)

        assert_that(result, equal_to(expected(self.contact_1)))

    @with_user_uuid
    @with_user_uuid
    def test_get_personal_contact_from_another_user(self, user_1_uuid, user_2_uuid):
        contact_uuid, _, __ = self._insert_personal_contacts(
            user_1_uuid, self.contact_1, self.contact_2, self.contact_3
        )

        assert_that(
            calling(self._crud.get_personal_contact).with_args(
                user_2_uuid, contact_uuid
            ),
            raises(exception.NoSuchContact),
        )

    @with_user_uuid
    def test_delete_personal_contact(self, user_uuid):
        (contact_uuid,) = self._insert_personal_contacts(user_uuid, self.contact_1)

        self._crud.delete_personal_contact(user_uuid, contact_uuid)

        assert_that(
            calling(self._crud.get_personal_contact).with_args(user_uuid, contact_uuid),
            raises(exception.NoSuchContact),
        )

    @with_user_uuid
    @with_user_uuid
    def test_delete_personal_contact_from_another_user(self, user_1_uuid, user_2_uuid):
        (contact_uuid,) = self._insert_personal_contacts(user_1_uuid, self.contact_1)

        assert_that(
            calling(self._crud.delete_personal_contact).with_args(
                user_2_uuid, contact_uuid
            ),
            raises(exception.NoSuchContact),
        )

    @with_user_uuid
    @with_user_uuid
    def test_delete_all_personal_contact_from_another_user(
        self, user_1_uuid, user_2_uuid
    ):
        (contact_uuid_1,) = self._insert_personal_contacts(user_1_uuid, self.contact_1)
        contact_uuid_2, contact_uuid_3 = self._insert_personal_contacts(
            user_2_uuid, self.contact_2, self.contact_3
        )

        self._crud.delete_all_personal_contacts(user_2_uuid)

        assert_that(
            calling(self._crud.get_personal_contact).with_args(
                user_1_uuid, contact_uuid_1
            ),
            not_(raises(exception.NoSuchContact)),
        )
        assert_that(
            calling(self._crud.get_personal_contact).with_args(
                user_2_uuid, contact_uuid_2
            ),
            raises(exception.NoSuchContact),
        )
        assert_that(
            calling(self._crud.get_personal_contact).with_args(
                user_2_uuid, contact_uuid_3
            ),
            raises(exception.NoSuchContact),
        )


class TestFavoriteCrud(_BaseTest):
    def setUp(self):
        super().setUp()
        self._crud = database.FavoriteCRUD(Session)

    @fixtures.source(backend='backend', name='foobar')
    def test_that_create_creates_a_favorite(self, source):
        user_uuid = new_uuid()
        source_name = 'foobar'
        contact_id = 'the-contact-id'
        backend = 'backend'

        favorite = self._crud.create(
            user_uuid, TENANT_UUID, backend, source_name, contact_id
        )

        assert_that(favorite.user_uuid, equal_to(user_uuid))
        assert_that(favorite.contact_id, equal_to(contact_id))

        assert_that(self._user_exists(TENANT_UUID, user_uuid))
        assert_that(
            self._favorite_exists(TENANT_UUID, user_uuid, source_name, contact_id)
        )

    @with_user_uuid
    @fixtures.source(backend='backend', name='source')
    def test_that_creating_the_same_favorite_raises(self, source, user_uuid):
        source, contact_id, backend = 'source', 'the-contact-id', 'backend'
        self._crud.create(user_uuid, TENANT_UUID, backend, source, contact_id)
        assert_that(
            calling(self._crud.create).with_args(
                user_uuid, TENANT_UUID, backend, source, contact_id
            ),
            raises(exception.DuplicatedFavoriteException),
        )

    @with_user_uuid
    @with_user_uuid
    @fixtures.source(name='s1')
    @fixtures.source(name='s2')
    @fixtures.source(name='s3')
    def test_get(self, source_3, source_2, source_1, user_1, user_2):
        backend = source_1['backend']

        self._crud.create(user_1, TENANT_UUID, backend, 's1', '1')
        self._crud.create(user_1, TENANT_UUID, backend, 's2', '1')
        self._crud.create(user_1, TENANT_UUID, backend, 's1', '42')
        self._crud.create(user_2, TENANT_UUID, backend, 's1', '42')
        self._crud.create(user_2, TENANT_UUID, backend, 's3', '1')

        fav_1 = self._crud.get(user_1)
        fav_2 = self._crud.get(user_2)

        assert_that(fav_1, contains_inanyorder(('s1', '1'), ('s2', '1'), ('s1', '42')))
        assert_that(fav_2, contains_inanyorder(('s1', '42'), ('s3', '1')))

    @fixtures.source(backend='backend', name='source')
    @with_user_uuid
    def test_that_delete_removes_a_favorite(self, user_uuid, source):
        backend = 'backend'
        self._crud.create(user_uuid, TENANT_UUID, backend, 'source', 'the-contact-id')

        self._crud.delete(user_uuid, 'source', 'the-contact-id')

        assert_that(
            self._favorite_exists(TENANT_UUID, user_uuid, 'source', 'the-contact-id'),
            equal_to(False),
        )

    @fixtures.source(backend='backend', name='source')
    @with_user_uuid
    @with_user_uuid
    def test_that_delete_does_not_remove_favorites_from_other_users(
        self, user_1, user_2, source
    ):
        backend = 'backend'
        self._crud.create(user_2, TENANT_UUID, backend, 'source', 'the-contact-id')

        assert_that(
            calling(self._crud.delete).with_args(user_1, 'source', 'the-contact-id'),
            raises(exception.NoSuchFavorite),
        )

        assert_that(
            self._favorite_exists(TENANT_UUID, user_2, 'source', 'the-contact-id')
        )

    @fixtures.source(backend='backend', name='source')
    @with_user_uuid
    def test_that_delete_raises_if_not_found(self, user_uuid, source):
        assert_that(
            calling(self._crud.delete).with_args(user_uuid, 'source', 'the-contact-id'),
            raises(exception.NoSuchFavorite),
        )

    @fixtures.source(backend='backend', name='source')
    @with_user_uuid
    def test_that_delete_from_an_unknown_source_raises(self, user_uuid, source):
        backend = 'backend'
        self._crud.create(user_uuid, TENANT_UUID, backend, 'source', 'the-contact-id')

        assert_that(
            calling(self._crud.delete).with_args(
                user_uuid, 'not-source', 'the-contact-id'
            ),
            raises(exception.NoSuchFavorite),
        )

    def _user_exists(self, tenant_uuid, user_uuid):
        with closing(Session()) as session:
            user_uuid = (
                session.query(database.User.user_uuid)
                .filter(
                    and_(
                        database.User.user_uuid == user_uuid,
                        database.User.tenant_uuid == tenant_uuid,
                    )
                )
                .scalar()
            )

        return user_uuid is not None

    def _favorite_exists(self, tenant_uuid, user_uuid, source_name, contact_id):
        with closing(Session()) as session:
            favorite = (
                session.query(database.Favorite)
                .join(database.Source)
                .join(database.User)
                .filter(
                    and_(
                        database.User.user_uuid == user_uuid,
                        database.User.tenant_uuid == tenant_uuid,
                        database.Source.name == source_name,
                        database.Favorite.contact_id == contact_id,
                    )
                )
            ).first()

        return favorite is not None


class TestPhonebookContactSearchEngine(_BaseTest):
    tenant_uuid = new_uuid()

    def setUp(self):
        super().setUp()
        self.phonebook_crud = database.PhonebookCRUD(Session)
        self.phonebook_contact_crud = database.PhonebookContactCRUD(Session)
        self.phonebook = self.phonebook_crud.create(self.tenant_uuid, {'name': 'test'})
        self.phonebook_uuid = self.phonebook['uuid']
        bodies = [
            {'firstname': 'Mia', 'lastname': 'Wallace', 'number': '5551111111'},
            {'firstname': 'Marcellus', 'lastname': 'Wallace', 'number': '5551111111'},
            {'firstname': 'Vincent', 'lastname': 'Vega', 'number': '5552222222'},
            {'firstname': 'Jules', 'lastname': 'Winnfield', 'number': '5553333333'},
            {'firstname': 'Butch', 'lastname': 'Coolidge'},
            {'firstname': 'Jimmie', 'lastname': 'Dimmick', 'number': '5554444444'},
        ]
        [
            self.mia,
            self.marcellus,
            self.vincent,
            self.jules,
            self.butch,
            self.jimmie,
        ] = [
            self.phonebook_contact_crud.create(
                [self.tenant_uuid],
                database.PhonebookKey(uuid=self.phonebook_uuid),
                body,
            )
            for body in bodies
        ]
        self.engine = database.PhonebookContactSearchEngine(
            Session,
            [self.tenant_uuid],
            database.PhonebookKey(uuid=self.phonebook_uuid),
            searched_columns=['lastname'],
            first_match_columns=['number'],
        )

    def tearDown(self):
        self.phonebook_crud.delete(
            [self.tenant_uuid], database.PhonebookKey(uuid=self.phonebook_uuid)
        )
        super().tearDown()

    def test_that_searching_personal_contacts_returns_the_searched_contacts(self):
        result = self.engine.find_contacts('w')

        assert_that(result, contains_inanyorder(self.mia, self.marcellus, self.jules))

    def test_that_none_matching_search_returns_an_empty_list(self):
        result = self.engine.find_contacts('mia')  # lastname search

        assert_that(result, empty())

    def test_that_no_searched_columns_does_not_search(self):
        engine = database.PhonebookContactSearchEngine(
            Session,
            [self.tenant_uuid],
            database.PhonebookKey(uuid=self.phonebook_uuid),
            first_match_columns=['number'],
        )
        result = engine.find_contacts('a')

        assert_that(result, empty())

    def test_that_find_first_returns_a_contact(self):
        result = self.engine.find_first_contact('5551111111')

        assert_that(result, any_of(self.mia, self.marcellus))

    def test_that_listing_contacts_works(self):
        result = self.engine.list_contacts(
            [self.mia['id'], self.butch['id'], self.jimmie['id']]
        )

        assert_that(result, contains_inanyorder(self.mia, self.butch, self.jimmie))

    def test_that_listing_is_limited_to_the_current_phonebook_and_tenant(self):
        shire_phonebook = self.phonebook_crud.create('lotr', {'name': 'shire'})
        frodo = self.phonebook_contact_crud.create(
            ['lotr'],
            database.PhonebookKey(uuid=shire_phonebook['uuid']),
            {'firstname': 'Frodo', 'lastname': 'Baggins'},
        )

        result = self.engine.list_contacts(
            [self.mia['id'], frodo['id'], self.jimmie['id']]
        )

        assert_that(result, contains_inanyorder(self.mia, self.jimmie))


class TestPersonalContactSearchEngine(_BaseTest):
    @with_user_uuid
    def test_that_find_first_returns_a_contact(self, user_uuid):
        engine = database.PersonalContactSearchEngine(
            Session, first_match_columns=['number']
        )

        self._insert_personal_contacts(
            user_uuid, self.contact_1, self.contact_2, self.contact_3
        )

        result = engine.find_first_personal_contact(user_uuid, '5555550001')

        assert_that(
            result, contains(any_of(expected(self.contact_2), expected(self.contact_3)))
        )

    @with_user_uuid
    def test_that_listing_personal_contacts_returns_the_searched_contacts(
        self, user_uuid
    ):
        engine = database.PersonalContactSearchEngine(
            Session, searched_columns=['firstname']
        )

        ids = self._insert_personal_contacts(user_uuid, self.contact_1, self.contact_2)

        result = engine.list_personal_contacts(user_uuid, ids)
        assert_that(
            result,
            contains_inanyorder(expected(self.contact_1), expected(self.contact_2)),
        )

        result = engine.list_personal_contacts(user_uuid, ids[:1])
        assert_that(result, contains(expected(self.contact_1)))

        result = engine.list_personal_contacts(user_uuid, ids[1:])
        assert_that(result, contains(expected(self.contact_2)))

    @with_user_uuid
    @with_user_uuid
    def test_that_listing_personal_contacts_only_the_users_contact(
        self, uuid_1, uuid_2
    ):
        engine = database.PersonalContactSearchEngine(
            Session, searched_columns=['firstname']
        )

        ids_1 = self._insert_personal_contacts(uuid_1, self.contact_1, self.contact_2)
        ids_2 = self._insert_personal_contacts(uuid_2, self.contact_1, self.contact_3)

        result = engine.list_personal_contacts(uuid_1, ids_1)
        assert_that(
            result,
            contains_inanyorder(expected(self.contact_1), expected(self.contact_2)),
        )

        result = engine.list_personal_contacts(uuid_2, ids_2)
        assert_that(
            result,
            contains_inanyorder(expected(self.contact_1), expected(self.contact_3)),
        )

        result = engine.list_personal_contacts(uuid_1, ids_2)
        assert_that(result, empty())

        result = engine.list_personal_contacts(uuid_2, ids_1)
        assert_that(result, empty())

    @with_user_uuid
    def test_that_searching_for_a_contact_returns_its_fields(self, user_uuid):
        engine = database.PersonalContactSearchEngine(
            Session, searched_columns=['firstname']
        )

        self._insert_personal_contacts(user_uuid, self.contact_1, self.contact_2)

        result = engine.find_personal_contacts(user_uuid, 'ced')
        assert_that(result, contains(expected(self.contact_2)))

        result = engine.find_personal_contacts(user_uuid, 'céd')
        assert_that(result, contains(expected(self.contact_2)))

    @with_user_uuid
    def test_that_find_searches_only_in_searched_columns(self, user_uuid):
        engine = database.PersonalContactSearchEngine(
            Session, searched_columns=['lastname']
        )

        self._insert_personal_contacts(user_uuid, self.contact_1, self.contact_2)

        result = engine.find_personal_contacts(user_uuid, 'ced')

        assert_that(result, empty())

    @with_user_uuid
    def test_that_no_searched_columns_does_not_search(self, user_uuid):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=[])

        self._insert_personal_contacts(user_uuid, self.contact_1, self.contact_2)

        result = engine.find_personal_contacts(user_uuid, 'ced')

        assert_that(result, empty())


class TestProfileCRUD(_BaseTest):
    @fixtures.display(tenant_uuid=TENANT_UUID)
    @fixtures.source(tenant_uuid=TENANT_UUID)
    @fixtures.source(tenant_uuid=TENANT_UUID)
    def test_create_no_error(self, source_2, source_1, display):
        name = 'my-profile'
        body = {
            'tenant_uuid': TENANT_UUID,
            'name': name,
            'display': {'uuid': display['uuid']},
            'services': {
                'lookup': {
                    'sources': [{'uuid': source_1['uuid']}, {'uuid': source_2['uuid']}],
                    'timeout': 5,
                },
                'reverse': {'sources': [{'uuid': source_2['uuid']}], 'timeout': 0.5},
            },
        }

        result = self.profile_crud.create(body)

        try:
            assert_that(
                result,
                has_entries(
                    uuid=uuid_(),
                    tenant_uuid=TENANT_UUID,
                    name=name,
                    display=has_entries(uuid=display['uuid']),
                    services=has_entries(
                        lookup=has_entries(
                            sources=contains(
                                has_entries(uuid=source_1['uuid']),
                                has_entries(uuid=source_2['uuid']),
                            ),
                            timeout=5,
                        ),
                        reverse=has_entries(
                            sources=contains(has_entries(uuid=source_2['uuid'])),
                            timeout=0.5,
                        ),
                    ),
                ),
            )
        finally:
            self.profile_crud.delete(None, result['uuid'])

    @fixtures.source(tenant_uuid=TENANT_UUID)
    @fixtures.source(tenant_uuid=TENANT_UUID)
    def test_create_unknown_display(self, source_2, source_1):
        body = {
            'tenant_uuid': TENANT_UUID,
            'name': 'profile',
            'display': {'uuid': 'b20524b7-7c87-4b0d-ba22-19656a77c3e2'},
            'services': {},
        }

        assert_that(
            calling(self.profile_crud.create).with_args(body),
            raises(exception.NoSuchDisplay),
        )

    @fixtures.display(tenant_uuid=TENANT_UUID)
    def test_create_unknown_source(self, display):
        body = {
            'tenant_uuid': TENANT_UUID,
            'name': 'profile',
            'display_uuid': None,
            'services': {
                'lookup': {
                    'sources': [{'uuid': 'eb124746-09be-44db-b01d-5b7dc1ea59a3'}]
                }
            },
        }

        assert_that(
            calling(self.profile_crud.create).with_args(body),
            raises(exception.NoSuchSource),
        )

        body = {
            'tenant_uuid': new_uuid(),
            'name': 'profile',
            'display_uuid': None,
            'services': {'lookup': {'sources': [{'id': 42}]}},
        }

        assert_that(
            calling(self.profile_crud.create).with_args(body),
            raises(exception.NoSuchSource),
        )

    @fixtures.display(
        uuid='b76f21a2-c1ab-4f4c-b71e-dac6c7c18275',
        tenant_uuid='f537dcbf-2504-428f-967d-503cf7cbb66d',
        columns=[{'title': 'Firstname', 'field': 'firstname'}],
    )
    @fixtures.source(
        uuid='91c48535-5104-4052-9b85-7a3b211ea1b0',
        tenant_uuid='f537dcbf-2504-428f-967d-503cf7cbb66d',
    )
    @fixtures.source(
        uuid='a36ce082-03ac-40c6-95d9-8b06fc2ea788',
        tenant_uuid='f537dcbf-2504-428f-967d-503cf7cbb66d',
    )
    @fixtures.profile(
        name='detailed',
        tenant_uuid='f537dcbf-2504-428f-967d-503cf7cbb66d',
        display={'uuid': 'b76f21a2-c1ab-4f4c-b71e-dac6c7c18275'},
        services={
            'lookup': {
                'sources': [
                    {'uuid': '91c48535-5104-4052-9b85-7a3b211ea1b0'},
                    {'uuid': 'a36ce082-03ac-40c6-95d9-8b06fc2ea788'},
                ],
                'timeout': 3,
            },
            'reverse': {
                'sources': [{'uuid': '91c48535-5104-4052-9b85-7a3b211ea1b0'}],
                'timeout': 0.5,
            },
        },
    )
    def test_get_detailed(self, profile, source_2, source_1, display):
        tenant_uuid = 'f537dcbf-2504-428f-967d-503cf7cbb66d'

        result = self.profile_crud.get([tenant_uuid], profile['uuid'])

        assert_that(
            result,
            has_entries(
                uuid=profile['uuid'],
                name=profile['name'],
                tenant_uuid=profile['tenant_uuid'],
                display=display,
                services=has_entries(
                    lookup=has_entries(
                        sources=contains_inanyorder(
                            has_entries(
                                uuid=source_1['uuid'], backend=source_1['backend']
                            ),
                            has_entries(
                                uuid=source_2['uuid'], backend=source_2['backend']
                            ),
                        ),
                        timeout=3,
                    ),
                    reverse=has_entries(
                        sources=contains_inanyorder(
                            has_entries(
                                uuid=source_1['uuid'], backend=source_1['backend']
                            )
                        ),
                        timeout=0.5,
                    ),
                ),
            ),
        )

    @fixtures.profile(
        name='one',
        tenant_uuid='f537dcbf-2504-428f-967d-503cf7cbb66d',
        display=None,
        services={},
    )
    @fixtures.profile(
        name='two',
        tenant_uuid='f537dcbf-2504-428f-967d-503cf7cbb66d',
        display=None,
        services={},
    )
    @fixtures.profile(
        name='three',
        tenant_uuid='f537dcbf-2504-428f-967d-503cf7cbb66d',
        display=None,
        services={},
    )
    def test_list(self, three, two, one):
        tenant_uuid = 'f537dcbf-2504-428f-967d-503cf7cbb66d'

        result = self.profile_crud.list_([tenant_uuid])
        assert_that(result, contains_inanyorder(one, two, three))

        result = self.profile_crud.list_([tenant_uuid], name='one')
        assert_that(result, contains_inanyorder(one))

        result = self.profile_crud.list_(None)
        assert_that(result, contains_inanyorder(one, two, three))

        result = self.profile_crud.list_(None, name='one')
        assert_that(result, contains_inanyorder(one))

        result = self.profile_crud.list_([])
        assert_that(result, empty())

        result = self.profile_crud.list_(['2cbe9aba-6f15-4907-9fa6-9efb0b65028b'])
        assert_that(result, empty())

    @fixtures.profile(
        name='one',
        tenant_uuid='f537dcbf-2504-428f-967d-503cf7cbb66d',
        display=None,
        services={},
    )
    @fixtures.profile(
        name='two',
        tenant_uuid='f537dcbf-2504-428f-967d-503cf7cbb66d',
        display=None,
        services={},
    )
    @fixtures.profile(
        name='three',
        tenant_uuid='76e03904-efa5-4885-a824-cfa5701da777',
        display=None,
        services={},
    )
    def test_list_multi_tenant(self, three, two, one):
        tenant_uuid = 'f537dcbf-2504-428f-967d-503cf7cbb66d'

        result = self.profile_crud.list_([tenant_uuid])
        assert_that(result, contains_inanyorder(one, two))

        result = self.profile_crud.list_([tenant_uuid], name='three')
        assert_that(result, empty())

    @fixtures.profile()
    def test_delete(self, profile):
        unknown_uuid = '26f11ad0-e509-4208-92bf-ce55afae9267'

        assert_that(
            calling(self.profile_crud.delete).with_args(None, unknown_uuid),
            raises(exception.NoSuchProfileAPIException),
        )

        assert_that(
            calling(self.profile_crud.delete).with_args(
                [unknown_uuid], profile['uuid']
            ),
            raises(exception.NoSuchProfileAPIException),
        )

        assert_that(
            calling(self.profile_crud.delete).with_args([], profile['uuid']),
            raises(exception.NoSuchProfileAPIException),
        )

        assert_that(
            calling(self.profile_crud.delete).with_args(
                [profile['tenant_uuid']], profile['uuid']
            ),
            not_(raises(Exception)),
        )


class TestTenantCRUD(_BaseTest):
    def setUp(self):
        super().setUp()
        self._crud = database.TenantCRUD(Session)

    def test_create_and_update(self):
        result = self._crud.create(tenant_uuid=TENANT_UUID)
        assert result == {'uuid': TENANT_UUID, 'country': None}

        result = self._crud.create(tenant_uuid=TENANT_UUID, country='CA')
        assert result == {'uuid': TENANT_UUID, 'country': 'CA'}
