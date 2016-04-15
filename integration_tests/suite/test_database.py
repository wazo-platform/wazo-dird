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

from hamcrest import assert_that, contains, empty
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


def expected(contact, unique_column='id'):
    result = {unique_column: ANY}
    result.update(contact)
    return result


def with_user_uuid(f):
    uuid = new_uuid()

    @functools.wraps(f)
    def wrapped(self, *args, **kwargs):
        user = database.User(xivo_user_uuid=uuid)
        self.session.add(user)
        self.session.flush()
        result = f(self, uuid, *args, **kwargs)
        self.session.query(database.User).filter(database.User.xivo_user_uuid == uuid).delete()
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

    def setUp(self):
        self.session = Session()

    @with_user_uuid
    def test_that_searching_for_a_contact_returns_its_fields(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(self.session, searched_columns=['firstname'])

        self._insert_personal_contacts(xivo_user_uuid, CONTACT_1, CONTACT_2)

        result = engine.find_personal_contacts(xivo_user_uuid, 'rai')

        assert_that(result, contains(expected(CONTACT_2)))

    @with_user_uuid
    def test_that_the_unique_column_is_named_correctly(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(
            self.session, unique_column='uuid', searched_columns=['firstname'])

        self._insert_personal_contacts(xivo_user_uuid, CONTACT_1, CONTACT_2)

        result = engine.find_personal_contacts(xivo_user_uuid, 'rai')

        assert_that(result, contains(expected(CONTACT_2, 'uuid')))

    @with_user_uuid
    def test_that_find_searches_only_in_searched_columns(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(
            self.session, unique_column='uuid', searched_columns=['lastname'])

        self._insert_personal_contacts(xivo_user_uuid, CONTACT_1, CONTACT_2)

        result = engine.find_personal_contacts(xivo_user_uuid, 'rai')

        assert_that(result, empty())

    @with_user_uuid
    def test_that_no_searched_columns_does_not_search(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(
            self.session, unique_column='uuid', searched_columns=[])

        self._insert_personal_contacts(xivo_user_uuid, CONTACT_1, CONTACT_2)

        result = engine.find_personal_contacts(xivo_user_uuid, 'rai')

        assert_that(result, empty())

    def _insert_personal_contacts(self, xivo_user_uuid, *contacts):
        for contact in contacts:
            dird_contact = database.Contact(user_uuid=xivo_user_uuid)
            self.session.add(dird_contact)
            self.session.flush()
            for name, value in contact.iteritems():
                field = database.ContactFields(name=name, value=value, contact_uuid=dird_contact.uuid)
                self.session.add(field)
        self.session.flush()
