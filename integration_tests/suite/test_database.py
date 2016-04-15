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

import uuid
import unittest
import os

from hamcrest import assert_that, contains
from mock import ANY

from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import create_engine

from xivo_dird import database


Session = sessionmaker()


def new_uuid():
    return str(uuid.uuid4())


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

    def test_that_searching_for_a_contact_returns_its_fields(self):
        xivo_user_uuid = new_uuid()
        contacts = [{'firtname': 'Finley',
                     'lastname': 'Shelley',
                     'number': '5555551111'},
                    {'firstname': 'Rain',
                     'lastname': 'Ora',
                     'number': '5555550001'}]
        self._insert_personal_contacts(xivo_user_uuid, contacts)

        result = database.find_personal_contacts(self.session, xivo_user_uuid, 'rai')

        expected = dict(contacts[1])
        expected['id'] = ANY
        assert_that(result, contains(expected))

    def _insert_personal_contacts(self, xivo_user_uuid, contacts):
        user = database.User(xivo_user_uuid=xivo_user_uuid)
        self.session.add(user)
        self.session.flush()
        for contact in contacts:
            dird_contact = database.Contact(user_uuid=user.xivo_user_uuid)
            self.session.add(dird_contact)
            self.session.flush()
            for name, value in contact.iteritems():
                field = database.ContactFields(name=name, value=value, contact_uuid=dird_contact.uuid)
                self.session.add(field)
        self.session.flush()
