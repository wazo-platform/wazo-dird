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

from hamcrest import assert_that, any_of, contains, contains_inanyorder, empty
from mock import ANY

from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import create_engine

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


def expected(contact, unique_column='id'):
    result = {unique_column: ANY}
    result.update(contact)
    return result


def with_user_uuid(f):
    uuid = new_uuid()

    @functools.wraps(f)
    def wrapped(self, *args, **kwargs):
        user = database.User(xivo_user_uuid=uuid)
        session = Session()
        session.add(user)
        session.commit()
        result = f(self, uuid, *args, **kwargs)
        session.query(database.User).filter(database.User.xivo_user_uuid == uuid).delete()
        session.commit()
        return result
    return wrapped


class TestContacts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db_uri = os.getenv('DB_URI', None)
        engine = create_engine(db_uri)
        database.Base.metadata.bind = engine
        database.Base.metadata.reflect()
        database.Base.metadata.drop_all()
        database.Base.metadata.create_all()

    @with_user_uuid
    def test_that_find_first_returns_a_contact(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, first_match_columns=['number'])

        self._insert_personal_contacts(xivo_user_uuid, CONTACT_1, CONTACT_2, CONTACT_3)

        result = engine.find_first_personal_contact(xivo_user_uuid, '5555550001')

        assert_that(result, contains(any_of(expected(CONTACT_2), expected(CONTACT_3))))

    @with_user_uuid
    def test_that_listing_personal_contacts_returns_all_contacts(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=['firstname'])

        self._insert_personal_contacts(xivo_user_uuid, CONTACT_1, CONTACT_2)

        result = engine.list_personal_contacts(xivo_user_uuid)

        assert_that(result, contains_inanyorder(expected(CONTACT_1), expected(CONTACT_2)))

    @with_user_uuid
    @with_user_uuid
    def test_that_listing_personal_contacts_only_the_users_contact(self, uuid_1, uuid_2):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=['firstname'])

        self._insert_personal_contacts(uuid_1, CONTACT_1, CONTACT_2)
        self._insert_personal_contacts(uuid_2, CONTACT_1, CONTACT_3)

        result = engine.list_personal_contacts(uuid_1)
        assert_that(result, contains_inanyorder(expected(CONTACT_1), expected(CONTACT_2)))

        result = engine.list_personal_contacts(uuid_2)
        assert_that(result, contains_inanyorder(expected(CONTACT_1), expected(CONTACT_3)))

    @with_user_uuid
    def test_that_searching_for_a_contact_returns_its_fields(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=['firstname'])

        self._insert_personal_contacts(xivo_user_uuid, CONTACT_1, CONTACT_2)

        result = engine.find_personal_contacts(xivo_user_uuid, 'rai')

        assert_that(result, contains(expected(CONTACT_2)))

    @with_user_uuid
    def test_that_the_unique_column_is_named_correctly(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(
            Session, unique_column='uuid', searched_columns=['firstname'])

        self._insert_personal_contacts(xivo_user_uuid, CONTACT_1, CONTACT_2)

        result = engine.find_personal_contacts(xivo_user_uuid, 'rai')

        assert_that(result, contains(expected(CONTACT_2, 'uuid')))

    @with_user_uuid
    def test_that_find_searches_only_in_searched_columns(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(
            Session, unique_column='uuid', searched_columns=['lastname'])

        self._insert_personal_contacts(xivo_user_uuid, CONTACT_1, CONTACT_2)

        result = engine.find_personal_contacts(xivo_user_uuid, 'rai')

        assert_that(result, empty())

    @with_user_uuid
    def test_that_no_searched_columns_does_not_search(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(
            Session, unique_column='uuid', searched_columns=[])

        self._insert_personal_contacts(xivo_user_uuid, CONTACT_1, CONTACT_2)

        result = engine.find_personal_contacts(xivo_user_uuid, 'rai')

        assert_that(result, empty())

    def _insert_personal_contacts(self, xivo_user_uuid, *contacts):
        session = Session()
        for contact in contacts:
            dird_contact = database.Contact(user_uuid=xivo_user_uuid)
            session.add(dird_contact)
            session.flush()
            for name, value in contact.iteritems():
                field = database.ContactFields(name=name, value=value, contact_uuid=dird_contact.uuid)
                session.add(field)
        session.commit()
