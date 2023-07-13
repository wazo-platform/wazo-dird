# Copyright 2016-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import random
import string
from typing import cast
import unittest

from uuid import uuid4
from unittest.mock import Mock
from hamcrest import assert_that, contains, contains_inanyorder, equal_to

from wazo_dird import database
from wazo_dird.database.queries.base import ContactInfo as _ContactInfo
from .helpers.base import DBRunningTestCase
from .helpers.utils import BackendWrapper

Session = None
DB_URI = None


class DBStarter(DBRunningTestCase):
    asset = 'database'


def setup_module():
    global Session
    global DB_URI
    DBStarter.setUpClass()
    Session = DBStarter.Session
    DB_URI = DBStarter.db_uri


def teardown_module():
    DBStarter.tearDownClass()


def _new_contact(firstname, lastname) -> dict[str, str]:
    random_number = ''.join(random.choice(string.digits) for _ in range(10))
    return {'firstname': firstname, 'lastname': lastname, 'number': random_number}


contact_bodies = [
    _new_contact('Albus', 'Dumbledore'),
    _new_contact('Hermione', 'Granger'),
    _new_contact('Rubeus', 'Hagrid'),
    _new_contact('Draco', 'Malfoy'),
    _new_contact('Harry', 'Potter'),
    _new_contact('Severus', 'Snape'),
    _new_contact('Ron', 'Weasley'),
]


class ContactInfo(_ContactInfo):
    firstname: str
    lastname: str
    number: str


contacts: list[ContactInfo] = []


class TestPhonebookBackend(unittest.TestCase):
    def setUp(self):
        global contacts
        self.tenant_uuid = str(uuid4())
        self.tenant = 'rowling'
        self.auth_client = Mock()
        self.auth_client.tenants.list.return_value = {
            'items': [{'uuid': self.tenant_uuid}]
        }
        self.token_renewer = Mock()
        self.phonebook_crud = database.PhonebookCRUD(Session)
        self.phonebook_contact_crud = database.PhonebookContactCRUD(Session)

        self.phonebook = self.phonebook_crud.create(
            self.tenant_uuid, {'name': 'hogwarts'}
        )
        contacts = cast(
            list[ContactInfo],
            [
                self.phonebook_contact_crud.create(
                    [self.tenant_uuid],
                    database.PhonebookKey(uuid=self.phonebook['uuid']),
                    cast(dict, c),
                )
                for c in contact_bodies
            ],
        )
        assert all(
            {'number', 'firstname', 'lastname'} & fields.keys() for fields in contacts
        )
        (
            self.dumbledore,
            self.hermione,
            self.hagrid,
            self.draco,
            self.harry,
            self.severus,
            self.ron,
        ) = contacts
        config = {
            'tenant_uuid': self.tenant_uuid,
            'name': 'hogwarts',
            'phonebook_id': self.phonebook['id'],
            'phonebook_uuid': self.phonebook['uuid'],
            'searched_columns': ['firstname', 'lastname'],
            'first_matched_columns': ['number'],
        }
        self.backend: BackendWrapper = self._load_backend(config)

    def _load_backend(self, config):
        dependencies = {
            'config': config,
            'auth_client': self.auth_client,
            'token_renewer': self.token_renewer,
        }
        return BackendWrapper('phonebook', dependencies)

    def tearDown(self):
        self.phonebook_crud.delete(
            [self.tenant_uuid], database.PhonebookKey(uuid=self.phonebook['uuid'])
        )

    def test_that_searching_for_grid_returns_agrid(self):
        result = self.backend.search('grid')

        assert_that(result, contains(self.hagrid))

    def test_that_first_match_returns_a_contact(self):
        result = self.backend.first(self.draco['number'])

        assert_that(result, equal_to(self.draco))

    def test_match_all_returns_the_expected_result(self):
        result = self.backend.match_all([self.draco['number'], '999999'])

        assert_that(result, contains_inanyorder(equal_to(self.draco)))

    def test_that_list_returns_the_contacts(self):
        result = self.backend.list(
            [self.hermione['id'], self.harry['id'], self.ron['id']]
        )

        assert_that(result, contains_inanyorder(self.hermione, self.harry, self.ron))
