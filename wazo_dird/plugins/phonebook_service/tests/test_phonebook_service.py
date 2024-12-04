# Copyright 2016-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest.mock import Mock
from unittest.mock import sentinel as s

from hamcrest import (
    assert_that,
    calling,
    contains,
    contains_inanyorder,
    contains_string,
    equal_to,
    has_entries,
    raises,
)

from wazo_dird import database
from wazo_dird.database.queries.phonebook import PhonebookKey
from wazo_dird.exception import InvalidContactException, InvalidPhonebookException

from ..plugin import PhonebookServicePlugin as Plugin
from ..plugin import _PhonebookService as Service


class TestPhonebookServicePlugin(unittest.TestCase):
    def setUp(self):
        self.args: dict = {'config': {}}

    def test_that_loading_without_a_proper_config_raises(self):
        plugin = Plugin()

        assert_that(calling(plugin.load).with_args({}), raises(ValueError))
        assert_that(calling(plugin.load).with_args({'config': {}}), raises(ValueError))


class _BasePhonebookServiceTest(unittest.TestCase):
    def setUp(self):
        self.phonebook_crud = Mock(database.PhonebookCRUD)
        self.contact_crud = Mock(database.PhonebookContactCRUD)
        self.service = Service(self.phonebook_crud, self.contact_crud)


class TestPhonebookPhonebookAPI(_BasePhonebookServiceTest):
    def test_list_phonebook(self):
        result = self.service.list_phonebook([s.tenant_uuid])

        assert_that(result, equal_to(self.phonebook_crud.list.return_value))

    def test_create_phonebook(self):
        body = {'name': 'a name'}

        result = self.service.create_phonebook(s.tenant_uuid, body)

        self.phonebook_crud.create.assert_called_once_with(s.tenant_uuid, body)
        assert_that(result, equal_to(self.phonebook_crud.create.return_value))

    def test_count_phonebook(self):
        result = self.service.count_phonebook([s.tenant_uuid], param1=s.param1)

        self.phonebook_crud.count.assert_called_once_with(
            [s.tenant_uuid], param1=s.param1
        )
        assert_that(result, equal_to(self.phonebook_crud.count.return_value))

    def test_that_create_with_no_name_raises(self):
        bodies = [{}, {'name': ''}, {'name': None}, None]
        for body in bodies:
            assert_that(
                calling(self.service.create_phonebook).with_args(s.tenant_uuid, body),
                raises(InvalidPhonebookException),
                body,
            )

    def test_edit_phonebook(self):
        body = {'name': 'foobar'}

        result = self.service.edit_phonebook(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), body
        )

        self.phonebook_crud.edit.assert_called_once_with(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), body
        )
        assert_that(result, equal_to(self.phonebook_crud.edit.return_value))

    def test_that_edit_with_no_name_raises(self):
        bodies = [{}, {'name': ''}, {'name': None}]
        for body in bodies:
            assert_that(
                calling(self.service.edit_phonebook).with_args(
                    [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), body
                ),
                raises(InvalidPhonebookException),
                body,
            )

    def test_delete_phonebook(self):
        self.service.delete_phonebook(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid)
        )

        self.phonebook_crud.delete.assert_called_once_with(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid)
        )

    def test_get_phonebook(self):
        result = self.service.get_phonebook(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid)
        )

        assert_that(result, equal_to(self.phonebook_crud.get.return_value))
        self.phonebook_crud.get.assert_called_once_with(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid)
        )


class TestPhonebookServiceContactAPI(_BasePhonebookServiceTest):
    def test_count_contact(self):
        result = self.service.count_contact(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid)
        )

        assert_that(result, equal_to(self.contact_crud.count.return_value))
        self.contact_crud.count.assert_called_once_with(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid)
        )

    def test_count_contact_with_a_search_param(self):
        result = self.service.count_contact(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), search=s.search
        )

        assert_that(result, equal_to(self.contact_crud.count.return_value))
        self.contact_crud.count.assert_called_once_with(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), search=s.search
        )

    def test_create_contact(self):
        body = {'firstname': 'foobar'}

        result = self.service.create_contact(
            s.tenant_uuid, PhonebookKey(uuid=s.phonebook_uuid), body
        )

        assert_that(result, equal_to(self.contact_crud.create.return_value))
        self.contact_crud.create.assert_called_once_with(
            s.tenant_uuid, PhonebookKey(uuid=s.phonebook_uuid), body
        )

    def test_that_the_id_field_should_be_ignored_on_create(self):
        result = self.service.create_contact(
            s.tenant_uuid,
            PhonebookKey(uuid=s.phonebook_uuid),
            {'firstname': 'bob', 'id': s.uuid},
        )

        assert_that(result, equal_to(self.contact_crud.create.return_value))
        self.contact_crud.create.assert_called_once_with(
            s.tenant_uuid, PhonebookKey(uuid=s.phonebook_uuid), {'firstname': 'bob'}
        )

    def test_that_create_contact_raises_for_invalid_input(self):
        invalid_bodies = [{'': 'Foo'}, {}]
        for body in invalid_bodies:
            assert_that(
                calling(self.service.create_contact).with_args(
                    s.tenant_uuid, PhonebookKey(uuid=s.phonebook_uuid), body
                ),
                raises(InvalidContactException),
                body,
            )

    def test_edit_contact(self):
        body = {'firstname': 'Foobar'}
        result = self.service.edit_contact(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), s.contact_uuid, body
        )

        assert_that(result, equal_to(self.contact_crud.edit.return_value))
        self.contact_crud.edit.assert_called_once_with(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), s.contact_uuid, body
        )

    def test_that_edit_contact_ignores_the_id_field(self):
        result = self.service.edit_contact(
            [s.tenant_uuid],
            PhonebookKey(uuid=s.phonebook_uuid),
            s.contact_uuid,
            {'firstname': 'alice', 'id': s.uuid},
        )

        assert_that(result, equal_to(self.contact_crud.edit.return_value))
        self.contact_crud.edit.assert_called_once_with(
            [s.tenant_uuid],
            PhonebookKey(uuid=s.phonebook_uuid),
            s.contact_uuid,
            {'firstname': 'alice'},
        )

    def test_that_edit_contact_raises_for_invalid_input(self):
        invalid_bodies = [{'': 'Foo'}, {}]
        for body in invalid_bodies:
            assert_that(
                calling(self.service.edit_contact).with_args(
                    [s.tenant_uuid],
                    PhonebookKey(uuid=s.phonebook_uuid),
                    s.contact_uuid,
                    body,
                ),
                raises(InvalidContactException),
                body,
            )

    def test_delete_contact(self):
        result = self.service.delete_contact(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), s.contact_uuid
        )

        assert_that(result, equal_to(self.contact_crud.delete.return_value))
        self.contact_crud.delete.assert_called_once_with(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), s.contact_uuid
        )

    def test_get_contact(self):
        result = self.service.get_contact(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), s.contact_uuid
        )

        assert_that(result, equal_to(self.contact_crud.get.return_value))
        self.contact_crud.get.assert_called_once_with(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), s.contact_uuid
        )


class TestPhonebookServiceContactList(_BasePhonebookServiceTest):
    def setUp(self):
        super().setUp()
        self._manolo = {
            'firstname': 'Manolo',
            'lastname': 'Laporte-Carpentier',
            'number': '5551111234',
        }
        self._annabelle = {
            'firstname': 'Ännabelle',
            'lastname': 'Courval',
            'number': '5552221234',
        }
        self._gary_bob = {'firstname': 'Gary-Bob', 'lastname': 'Derome'}
        self._antonin = {
            'firstname': 'Antonin',
            'lastname': 'Mongeau',
            'number': '5554441234',
        }
        self._simon = {'firstname': 'Simon', 'lastname': "L'Espérance"}
        self._contacts = [
            self._manolo,
            self._annabelle,
            self._gary_bob,
            self._antonin,
            self._simon,
        ]

    def test_that_list_returns_the_db_result_when_no_pagination_or_sorting(self):
        self.contact_crud.list.return_value = self._contacts

        result = self.service.list_contacts(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), search=s.search
        )

        self.contact_crud.list.assert_called_once_with(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), search=s.search
        )
        assert_that(result, contains(*self._contacts))

    def test_that_list_can_be_limited(self):
        self.contact_crud.list.return_value = self._contacts

        result = self.service.list_contacts(
            [s.tenant_uuid],
            PhonebookKey(uuid=s.phonebook_uuid),
            search=s.search,
            limit=2,
        )

        self.contact_crud.list.assert_called_once_with(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), search=s.search
        )
        assert_that(result, contains(self._manolo, self._annabelle))

    def test_that_list_can_have_an_offset(self):
        self.contact_crud.list.return_value = self._contacts

        result = self.service.list_contacts(
            [s.tenant_uuid],
            PhonebookKey(uuid=s.phonebook_uuid),
            search=s.search,
            offset=3,
        )

        self.contact_crud.list.assert_called_once_with(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), search=s.search
        )
        assert_that(result, contains(self._antonin, self._simon))

    def test_that_limit_and_offset_work_togeter(self):
        self.contact_crud.list.return_value = self._contacts

        result = self.service.list_contacts(
            [s.tenant_uuid],
            PhonebookKey(uuid=s.phonebook_uuid),
            search=s.search,
            offset=1,
            limit=2,
        )

        self.contact_crud.list.assert_called_once_with(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), search=s.search
        )
        assert_that(result, contains(self._annabelle, self._gary_bob))

    def test_that_results_can_be_ordered(self):
        self.contact_crud.list.return_value = self._contacts

        result = self.service.list_contacts(
            [s.tenant_uuid],
            PhonebookKey(uuid=s.phonebook_uuid),
            search=s.search,
            order='firstname',
        )

        self.contact_crud.list.assert_called_once_with(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), search=s.search
        )
        assert_that(
            result,
            contains(
                self._annabelle,
                self._antonin,
                self._gary_bob,
                self._manolo,
                self._simon,
            ),
        )

    def test_that_results_can_be_ordered_by_an_unknown_column_with_no_effect(self):
        self.contact_crud.list.return_value = self._contacts

        result = self.service.list_contacts(
            [s.tenant_uuid],
            PhonebookKey(uuid=s.phonebook_uuid),
            search=s.search,
            order='number',
            direction='desc',
        )

        self.contact_crud.list.assert_called_once_with(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), search=s.search
        )
        assert_that(
            result,
            contains_inanyorder(
                self._manolo,
                self._antonin,
                self._annabelle,
                self._gary_bob,  # no number
                self._simon,
            ),
        )  # no number

    def test_that_the_direction_can_be_specified(self):
        self.contact_crud.list.return_value = self._contacts

        result = self.service.list_contacts(
            [s.tenant_uuid],
            PhonebookKey(uuid=s.phonebook_uuid),
            search=s.search,
            order='firstname',
            direction='desc',
        )

        self.contact_crud.list.assert_called_once_with(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), search=s.search
        )
        assert_that(
            result,
            contains(
                self._simon,
                self._manolo,
                self._gary_bob,
                self._antonin,
                self._annabelle,
            ),
        )

    def test_all(self):
        self.contact_crud.list.return_value = self._contacts

        result = self.service.list_contacts(
            [s.tenant_uuid],
            PhonebookKey(uuid=s.phonebook_uuid),
            search=s.search,
            order='lastname',
            direction='desc',
            limit=3,
            offset=1,
        )

        self.contact_crud.list.assert_called_once_with(
            [s.tenant_uuid], PhonebookKey(uuid=s.phonebook_uuid), search=s.search
        )
        assert_that(result, contains(self._manolo, self._simon, self._gary_bob))


class TestPhonebookServiceContactImport(_BasePhonebookServiceTest):
    def test_import_with_invalid_contacts(self):
        db_errors = []
        self.contact_crud.create_many.return_value = [s.created], db_errors

        invalids: list[dict] = [{}, {'': 'test'}, {'firstname': 'Foo', None: ['extra']}]
        contacts: list[dict] = invalids + [{'firstname': 'Foo'}]
        created, errors = self.service.import_contacts(
            s.tenant_uuid, PhonebookKey(uuid=s.phonebook_uuid), contacts
        )
        assert len(created) + len(errors) == len(contacts)

        assert_that(created, equal_to([s.created]))
        assert_that(
            errors,
            contains_inanyorder(
                *db_errors,
                has_entries(
                    contact=invalids[0], message=contains_string('empty'), index=0
                ),
                has_entries(
                    contact=invalids[1], message=contains_string('empty key'), index=1
                ),
                has_entries(
                    contact=invalids[2], message=contains_string('null key'), index=2
                )
            ),
        )

    def test_import_with_database_error(self):
        db_errors = [
            {
                'index': 1,
                'contact': s.contact_1,
                'message': s.message_1,
            }
        ]
        self.contact_crud.create_many.return_value = [s.created1, s.created2], db_errors

        contacts: list[dict] = [
            {'firstname': 'Foo'},
            {'firstname': 'Foo'},
            {'firstname': 'Bar'},
        ]
        created, errors = self.service.import_contacts(
            s.tenant_uuid, PhonebookKey(uuid=s.phonebook_uuid), contacts
        )
        assert len(created) + len(errors) == len(contacts)

        assert_that(created, equal_to([s.created1, s.created2]))
        assert_that(
            errors,
            contains_inanyorder(
                has_entries(contact=s.contact_1, message=s.message_1, index=1)
            ),
        )

    def test_import_with_database_error_and_validation_error(self):
        contacts: list[dict] = [
            {'firstname': 'Foo'},
            {'': 'Foo'},
            {'firstname': 'Bar'},
        ]

        db_errors = [
            {
                'index': 1,
                'contact': contacts[2],
                'message': s.message_1,
            }
        ]
        self.contact_crud.create_many.return_value = [s.created1], db_errors

        created, errors = self.service.import_contacts(
            s.tenant_uuid, PhonebookKey(uuid=s.phonebook_uuid), contacts
        )
        assert len(created) + len(errors) == len(contacts)

        assert_that(created, equal_to([s.created1]))
        assert_that(
            errors,
            contains_inanyorder(
                has_entries(
                    contact=contacts[1], message=contains_string('empty key'), index=1
                ),
                has_entries(contact=contacts[2], message=s.message_1, index=2),
            ),
        )
