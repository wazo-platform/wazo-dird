# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import csv
import textwrap
import unittest
from typing import Any
from unittest.mock import Mock
from unittest.mock import sentinel as s

from hamcrest import assert_that, contains_exactly, contains_inanyorder, empty

from wazo_dird import database

from ..plugin import _PersonalService as Service

SOME_UUID = '29d4aec1-db4c-4c67-80a0-b83136c58a47'


def reader(document: str) -> csv.DictReader:
    return csv.DictReader(textwrap.dedent(document).splitlines())


class TestCreateContacts(unittest.TestCase):
    def setUp(self):
        self.crud = Mock(database.PersonalContactCRUD)
        self.service = Service(Mock(), Mock(), self.crud, Mock())

    def import_(
        self, document: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        return self.service.create_contacts(
            reader(document), s.user_uuid, s.tenant_uuid
        )

    def imported_rows(self) -> list[dict[str, Any]]:
        self.crud.create_personal_contacts.assert_called_once()
        tenant_uuid, user_uuid, rows = self.crud.create_personal_contacts.call_args[0]
        assert (tenant_uuid, user_uuid) == (s.tenant_uuid, s.user_uuid)
        return rows

    def test_that_an_id_column_no_longer_rejects_the_row(self):
        # The DAO generates the uuid and overwrites this value; the import has
        # no reason to look at it, let alone fail on it.
        _, errors = self.import_(
            f'''\
            id,firstname
            {SOME_UUID},alice
            '''
        )

        assert_that(errors, empty())
        assert_that(
            self.imported_rows(),
            contains_exactly({'id': SOME_UUID, 'firstname': 'alice'}),
        )

    def test_that_the_import_reads_no_contact_it_was_not_given(self):
        self.import_(
            '''\
            firstname
            alice
            '''
        )

        self.crud.list_personal_contacts.assert_not_called()

    def test_that_a_malformed_row_fails_with_its_line_and_the_others_import(self):
        _, errors = self.import_(
            '''\
            firstname,lastname
            alice,aldertion
            bob,bodkartan,too,many
            '''
        )

        assert_that(
            errors, contains_exactly({'errors': ['too many fields'], 'line': 3})
        )
        assert_that(
            self.imported_rows(),
            contains_exactly({'firstname': 'alice', 'lastname': 'aldertion'}),
        )


class TestValidateContact(unittest.TestCase):
    def test_that_an_empty_key_is_rejected(self):
        with self.assertRaises(Service.InvalidPersonalContact) as ctx:
            Service.validate_contact({'': 'alice'})

        assert_that(
            ctx.exception.errors, contains_inanyorder('"" is a forbidden in keys')
        )

    def test_that_a_non_string_value_is_rejected(self):
        with self.assertRaises(Service.InvalidPersonalContact) as ctx:
            Service.validate_contact({'firstname': 42})

        assert_that(
            ctx.exception.errors, contains_inanyorder('all values must be strings')
        )
