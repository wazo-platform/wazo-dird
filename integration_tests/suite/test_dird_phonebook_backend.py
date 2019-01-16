# Copyright 2016-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
import random
import string
import unittest

from hamcrest import assert_that, contains, contains_inanyorder, equal_to
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from wazo_dird import database
from .base_dird_integration_test import BaseDirdIntegrationTest, BackendWrapper

Session = scoped_session(sessionmaker())
DB_URI = None


class DBStarter(BaseDirdIntegrationTest):

    asset = 'database'


def setup_module():
    global DB_URI
    DBStarter.setUpClass()
    db_port = DBStarter.service_port(5432, 'db')
    DB_URI = os.getenv('DB_URI', 'postgresql://asterisk:proformatique@localhost:{port}'.format(port=db_port))
    engine = create_engine(DB_URI)
    database.Base.metadata.bind = engine
    database.Base.metadata.reflect()
    database.Base.metadata.drop_all()
    database.Base.metadata.create_all()


def teardown_module():
    DBStarter.tearDownClass()


def _new_contact(firstname, lastname):
    random_number = ''.join(random.choice(string.digits) for _ in range(10))
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

    def test_a_config_without_phonebook_id(self):
        config = {'config': {'name': 'dird_phonebook',
                             'db_uri': DB_URI,
                             'tenant': self.tenant,
                             'phonebook_name': 'hogwarts',
                             'searched_columns': ['firstname', 'lastname'],
                             'first_matched_columns': ['number']}}

        backend = BackendWrapper('dird_phonebook', config)

        result = backend.search('grid')

        assert_that(result, contains(self.hagrid))

    def test_that_searching_for_grid_returns_agrid(self):
        result = self.backend.search('grid')

        assert_that(result, contains(self.hagrid))

    def test_that_first_match_returns_a_contact(self):
        result = self.backend.first(self.draco['number'])

        assert_that(result, equal_to(self.draco))

    def test_that_list_returns_the_contacts(self):
        result = self.backend.list([self.hermione['id'], self.harry['id'], self.ron['id']])

        assert_that(result, contains_inanyorder(self.hermione, self.harry, self.ron))
