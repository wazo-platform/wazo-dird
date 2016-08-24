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

import os
import random
import string
import unittest

from hamcrest import assert_that, contains, contains_inanyorder, equal_to
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from stevedore import DriverManager

from xivo_dird import database
from xivo_dird.core.database import Base
from .base_dird_integration_test import BaseDirdIntegrationTest

Session = scoped_session(sessionmaker())
DB_URI = None


class DBStarter(BaseDirdIntegrationTest):

    asset = 'database'


def setup():
    global DB_URI
    DBStarter.setUpClass()
    DB_URI = os.getenv('DB_URI', 'postgresql://asterisk:proformatique@localhost:15432')
    engine = create_engine(DB_URI)
    Base.metadata.bind = engine
    Base.metadata.reflect()
    Base.metadata.drop_all()
    Base.metadata.create_all()


def teardown():
    DBStarter.tearDownClass()


def _new_contact(firstname, lastname):
    random_number = ''.join(random.choice(string.digits) for _ in xrange(10))
    return {'firstname': firstname,
            'lastname': lastname,
            'number': random_number}


contact_bodies = [
    _new_contact('Albus', 'Dumbledore'),
    _new_contact('Hermione', 'Granger'),
    _new_contact('Rubeus', 'Hagrid'),
    _new_contact('Draco', 'Malfoy'),
    _new_contact('Harry', 'Potter'),
    _new_contact('Severus', 'Snape'),
    _new_contact('Ron', 'Weasley'),
]
contacts = []


class BackendWrapper(object):

    def __init__(self, backend, config):
        manager = DriverManager(namespace='xivo_dird.backends',
                                name=backend,
                                invoke_on_load=True)
        self._source = manager.driver
        self._source.load(config)

    def search(self, term):
        results = self._source.search(term)
        return [r.fields for r in results]

    def first(self, term):
        return self._source.first_match(term).fields

    def list(self, source_ids):
        results = self._source.list(source_ids)
        return [r.fields for r in results]


class TestPhonebookBackend(unittest.TestCase):

    def setUp(self):
        global contacts
        self.tenant = 'rowling'
        self.phonebook_crud = database.PhonebookCRUD(Session)
        self.phonebook_contact_crud = database.PhonebookContactCRUD(Session)

        self.phonebook = self.phonebook_crud.create(self.tenant, {'name': 'hogwarts'})
        contacts = [self.phonebook_contact_crud.create(self.tenant, self.phonebook['id'], c)
                    for c in contact_bodies]
        (self.dumbledore,
         self.hermione,
         self.hagrid,
         self.draco,
         self.harry,
         self.severus,
         self.ron) = contacts
        self.config = {'config': {'name': 'dird_phonebook',
                                  'db_uri': DB_URI,
                                  'tenant': self.tenant,
                                  'phonebook_id': self.phonebook['id'],
                                  'searched_columns': ['firstname', 'lastname'],
                                  'first_matched_columns': ['number']}}
        self.backend = BackendWrapper('dird_phonebook', self.config)

    def tearDown(self):
        self.phonebook_crud.delete(self.tenant, self.phonebook['id'])

    def test_that_searching_for_grid_returns_agrid(self):
        result = self.backend.search('grid')

        assert_that(result, contains(self.hagrid))

    def test_that_first_match_returns_a_contact(self):
        result = self.backend.first(self.draco['number'])

        assert_that(result, equal_to(self.draco))

    def test_that_list_returns_the_contacts(self):
        result = self.backend.list([self.hermione['id'], self.harry['id'], self.ron['id']])

        assert_that(result, contains_inanyorder(self.hermione, self.harry, self.ron))
