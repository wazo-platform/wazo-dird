# -*- coding: utf-8 -*-

# Copyright (C) 2016 Avencall
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

import functools
import uuid
import unittest
import os

from hamcrest import (assert_that,
                      any_of,
                      calling,
                      contains,
                      contains_inanyorder,
                      empty,
                      equal_to,
                      not_,
                      raises)
from mock import ANY

from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker

from xivo_dird import database


Session = sessionmaker()


def new_uuid():
    return str(uuid.uuid4())

CONTACT_1 = {'firtname': 'Finley',
             'lastname': 'Shelley',
             'number': '5555551111'}
CONTACT_2 = {'firstname': 'Rain',
             'lastname': 'Ora',
             'number': '5555550001'}
CONTACT_3 = {'firstname': 'Foo',
             'lastname': 'Bar',
             'number': '5555550001'}


def expected(contact):
    result = {'id': ANY}
    result.update(contact)
    return result


def with_user_uuid(f):
    @functools.wraps(f)
    def wrapped(self, *args, **kwargs):
        user_uuid = new_uuid()
        user = database.User(xivo_user_uuid=user_uuid)
        session = Session()
        session.add(user)
        session.commit()
        result = f(self, user_uuid, *args, **kwargs)
        session.query(database.User).filter(database.User.xivo_user_uuid == user_uuid).delete()
        session.commit()
        return result
    return wrapped


db_initialized = False


def setup():
    global db_initialized
    if db_initialized is True:
        return

    db_uri = os.getenv('DB_URI', None)
    engine = create_engine(db_uri)
    database.Base.metadata.bind = engine
    database.Base.metadata.reflect()
    database.Base.metadata.drop_all()
    database.Base.metadata.create_all()
    db_initialized = True


class _BaseTest(unittest.TestCase):

    def _insert_personal_contacts(self, xivo_user_uuid, *contacts):
        ids = []
        session = Session()
        for contact in contacts:
            dird_contact = database.Contact(user_uuid=xivo_user_uuid)
            session.add(dird_contact)
            session.flush()
            ids.append(dird_contact.uuid)
            for name, value in contact.iteritems():
                field = database.ContactFields(name=name, value=value, contact_uuid=dird_contact.uuid)
                session.add(field)
        session.commit()
        return ids


class TestContactCRUD(_BaseTest):

    @classmethod
    def setUpClass(cls):
        setup()

    def setUp(self):
        self._session = Session()

    def tearDown(self):
        self._session.close()

    def test_that_create_personal_contact_creates_a_contact_and_the_owner(self):
        owner = new_uuid()

        result = database.create_personal_contact(self._session, owner, CONTACT_1)
        assert_that(result, equal_to(expected(CONTACT_1)))

        contact_list = database.list_personal_contacts(self._session, owner)
        assert_that(contact_list, contains(expected(CONTACT_1)))

    @with_user_uuid
    def test_that_create_personal_contact_creates_a_contact_with_an_existing_owner(self, xivo_user_uuid):
        result = database.create_personal_contact(self._session, xivo_user_uuid, CONTACT_1)
        assert_that(result, equal_to(expected(CONTACT_1)))

        contact_list = database.list_personal_contacts(self._session, xivo_user_uuid)
        assert_that(contact_list, contains(expected(CONTACT_1)))

    @with_user_uuid
    def test_get_personal_contact(self, xivo_user_uuid):
        contact_uuid, _, __ = self._insert_personal_contacts(xivo_user_uuid, CONTACT_1, CONTACT_2, CONTACT_3)

        result = database.get_personal_contact(self._session, xivo_user_uuid, contact_uuid)

        assert_that(result, equal_to(expected(CONTACT_1)))

    @with_user_uuid
    @with_user_uuid
    def test_get_personal_contact_from_another_user(self, user_1_uuid, user_2_uuid):
        contact_uuid, _, __ = self._insert_personal_contacts(user_1_uuid, CONTACT_1, CONTACT_2, CONTACT_3)

        assert_that(calling(database.get_personal_contact).with_args(self._session, user_2_uuid, contact_uuid),
                    raises(database.NoSuchPersonalContact))

    @with_user_uuid
    def test_delete_personal_contact(self, xivo_user_uuid):
        contact_uuid, = self._insert_personal_contacts(xivo_user_uuid, CONTACT_1)

        database.delete_personal_contact(self._session, xivo_user_uuid, contact_uuid)

        assert_that(calling(database.get_personal_contact).with_args(self._session, xivo_user_uuid, contact_uuid),
                    raises(database.NoSuchPersonalContact))

    @with_user_uuid
    @with_user_uuid
    def test_delete_personal_contact_from_another_user(self, user_1_uuid, user_2_uuid):
        contact_uuid, = self._insert_personal_contacts(user_1_uuid, CONTACT_1)

        database.delete_personal_contact(self._session, user_2_uuid, contact_uuid)

        assert_that(calling(database.get_personal_contact).with_args(self._session, user_1_uuid, contact_uuid),
                    not_(raises(database.NoSuchPersonalContact)))

    @with_user_uuid
    @with_user_uuid
    def test_delete_all_personal_contact_from_another_user(self, user_1_uuid, user_2_uuid):
        contact_uuid_1, = self._insert_personal_contacts(user_1_uuid, CONTACT_1)
        contact_uuid_2, contact_uuid_3 = self._insert_personal_contacts(user_2_uuid, CONTACT_2, CONTACT_3)

        database.delete_all_personal_contacts(self._session, user_2_uuid)

        assert_that(calling(database.get_personal_contact).with_args(self._session, user_1_uuid, contact_uuid_1),
                    not_(raises(database.NoSuchPersonalContact)))
        assert_that(calling(database.get_personal_contact).with_args(self._session, user_2_uuid, contact_uuid_2),
                    raises(database.NoSuchPersonalContact))
        assert_that(calling(database.get_personal_contact).with_args(self._session, user_2_uuid, contact_uuid_3),
                    raises(database.NoSuchPersonalContact))


class TestPersonalContactSearchEngine(_BaseTest):

    @classmethod
    def setUpClass(cls):
        setup()

    @with_user_uuid
    def test_that_find_first_returns_a_contact(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, first_match_columns=['number'])

        self._insert_personal_contacts(xivo_user_uuid, CONTACT_1, CONTACT_2, CONTACT_3)

        result = engine.find_first_personal_contact(xivo_user_uuid, '5555550001')

        assert_that(result, contains(any_of(expected(CONTACT_2), expected(CONTACT_3))))

    @with_user_uuid
    def test_that_listing_personal_contacts_returns_the_searched_contacts(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=['firstname'])

        ids = self._insert_personal_contacts(xivo_user_uuid, CONTACT_1, CONTACT_2)

        result = engine.list_personal_contacts(xivo_user_uuid, ids)
        assert_that(result, contains_inanyorder(expected(CONTACT_1), expected(CONTACT_2)))

        result = engine.list_personal_contacts(xivo_user_uuid, ids[:1])
        assert_that(result, contains(expected(CONTACT_1)))

        result = engine.list_personal_contacts(xivo_user_uuid, ids[1:])
        assert_that(result, contains(expected(CONTACT_2)))

    @with_user_uuid
    @with_user_uuid
    def test_that_listing_personal_contacts_only_the_users_contact(self, uuid_1, uuid_2):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=['firstname'])

        ids_1 = self._insert_personal_contacts(uuid_1, CONTACT_1, CONTACT_2)
        ids_2 = self._insert_personal_contacts(uuid_2, CONTACT_1, CONTACT_3)

        result = engine.list_personal_contacts(uuid_1, ids_1)
        assert_that(result, contains_inanyorder(expected(CONTACT_1), expected(CONTACT_2)))

        result = engine.list_personal_contacts(uuid_2, ids_2)
        assert_that(result, contains_inanyorder(expected(CONTACT_1), expected(CONTACT_3)))

        result = engine.list_personal_contacts(uuid_1, ids_2)
        assert_that(result, empty())

        result = engine.list_personal_contacts(uuid_2, ids_1)
        assert_that(result, empty())

    @with_user_uuid
    def test_that_searching_for_a_contact_returns_its_fields(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=['firstname'])

        self._insert_personal_contacts(xivo_user_uuid, CONTACT_1, CONTACT_2)

        result = engine.find_personal_contacts(xivo_user_uuid, 'rai')

        assert_that(result, contains(expected(CONTACT_2)))

    @with_user_uuid
    def test_that_find_searches_only_in_searched_columns(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=['lastname'])

        self._insert_personal_contacts(xivo_user_uuid, CONTACT_1, CONTACT_2)

        result = engine.find_personal_contacts(xivo_user_uuid, 'rai')

        assert_that(result, empty())

    @with_user_uuid
    def test_that_no_searched_columns_does_not_search(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=[])

        self._insert_personal_contacts(xivo_user_uuid, CONTACT_1, CONTACT_2)

        result = engine.find_personal_contacts(xivo_user_uuid, 'rai')

        assert_that(result, empty())
