# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import unittest

from uuid import uuid4
from hamcrest import assert_that
from hamcrest import equal_to
from hamcrest import not_
from hamcrest import none
from hamcrest import is_
from mock import Mock
from mock import patch
from mock import sentinel as s

from xivo_dird import database
from xivo_dird.plugins.personal_service import PersonalServicePlugin
from xivo_dird.plugins.personal_service import _PersonalService

SOME_UUID = str(uuid4())


class TestPersonalServicePlugin(unittest.TestCase):

    def setUp(self):
        self._crud = Mock(database.PersonalContactCRUD)

    def test_load_no_config(self):
        plugin = PersonalServicePlugin()

        self.assertRaises(ValueError, plugin.load, {})

    def test_that_load_returns_a_service(self):
        plugin = PersonalServicePlugin()
        plugin._new_personal_contact_crud = Mock()

        service = plugin.load({'config': {'db_uri': s.db_uri}, 'sources': {}})

        assert_that(service, not_(none()))

    @patch('xivo_dird.plugins.personal_service._PersonalService')
    def test_that_load_injects_config_and_sources_to_the_service(self, MockedPersonalService):
        plugin = PersonalServicePlugin()
        plugin._new_personal_contact_crud = Mock()

        config = {'db_uri': s.db_uri}
        service = plugin.load({'config': config, 'sources': {}})

        MockedPersonalService.assert_called_once_with(config, {}, plugin._new_personal_contact_crud.return_value)
        assert_that(service, equal_to(MockedPersonalService.return_value))

    def test_that_create_contact_calls_crud_create_contact(self):
        service = _PersonalService({}, {}, crud=self._crud)

        service.create_contact({'eyes': 'violet'}, {'token': 'valid-token',
                                                    'xivo_user_uuid': SOME_UUID})

        self._crud.create_personal_contact.assert_called_once_with(SOME_UUID, {'eyes': 'violet'})

    def test_that_list_contacts_calls_crud_list_personal_contacts(self):
        service = _PersonalService({}, {'personal': Mock(backend='personal')}, crud=self._crud)

        service.list_contacts({'token': 'valid-token', 'xivo_user_uuid': SOME_UUID})

        self._crud.list_personal_contacts.assert_called_once_with(SOME_UUID)

    def test_that_list_contacts_raw_calls_crud_list_personal_contacts(self):
        service = _PersonalService({'consul': {'host': 'localhost', 'port': 8500}}, {}, crud=self._crud)

        service.list_contacts_raw({'token': 'valid-token', 'xivo_user_uuid': SOME_UUID})

        self._crud.list_personal_contacts.assert_called_once_with(SOME_UUID)

    def test_that_get_contact_calls_crud_get_personal_contact(self):
        service = _PersonalService({'consul': {'host': 'localhost', 'port': 8500}}, {}, crud=self._crud)

        service.get_contact('contact-id', {'token': 'valid-token', 'xivo_user_uuid': SOME_UUID})

        self._crud.get_personal_contact.assert_called_once_with(SOME_UUID, 'contact-id')

    def test_that_edit_contact_calls_crud_edit_contact(self):
        service = _PersonalService({'consul': {'host': 'localhost', 'port': 8500}}, {}, crud=self._crud)

        service.edit_contact('contact-id', {'firstname': 'Alice'}, {'token': 'valid-token',
                                                                    'xivo_user_uuid': SOME_UUID})

        self._crud.edit_personal_contact.assert_called_once_with(SOME_UUID, 'contact-id', {'firstname': 'Alice'})

    def test_that_remove_contact_calls_crud_delete_personal_contact(self):
        service = _PersonalService({'consul': {'host': 'localhost', 'port': 8500}}, {}, crud=self._crud)

        service.remove_contact('my-contact-id', {'token': 'valid-token', 'xivo_user_uuid': SOME_UUID})

        self._crud.delete_personal_contact.assert_called_once_with(SOME_UUID, 'my-contact-id')

    def test_that_purge_contacts_calls_crud_delete_all_personal_contacts(self):
        service = _PersonalService({'consul': {'host': 'localhost', 'port': 8500}}, {}, crud=self._crud)

        service.purge_contacts({'token': 'valid-token', 'xivo_user_uuid': SOME_UUID})

        self._crud.delete_all_personal_contacts(SOME_UUID)


class TestValidateContact(unittest.TestCase):

    def test_that_validate_contact_refuses_dot_key(self):
        contact_infos = {
            '.': '.'
        }

        exception = _PersonalService.InvalidPersonalContact
        self.assertRaises(exception, _PersonalService.validate_contact, contact_infos)

    def test_that_validate_contact_refuses_non_ascii_key(self):
        contact_infos = {
            u'é': ''
        }

        exception = _PersonalService.InvalidPersonalContact
        self.assertRaises(exception, _PersonalService.validate_contact, contact_infos)

    def test_that_validate_contact_refuses_non_string_key(self):
        contact_infos = {
            1: '.'
        }

        exception = _PersonalService.InvalidPersonalContact
        self.assertRaises(exception, _PersonalService.validate_contact, contact_infos)

    def test_that_validate_contact_refuses_non_string_value(self):
        contact_infos = {
            'a': 2
        }

        exception = _PersonalService.InvalidPersonalContact
        self.assertRaises(exception, _PersonalService.validate_contact, contact_infos)

    def test_that_validate_contact_refuses_path_related_keys(self):
        exception = _PersonalService.InvalidPersonalContact
        self.assertRaises(exception, _PersonalService.validate_contact, {'/': '..'})
        self.assertRaises(exception, _PersonalService.validate_contact, {'//': '..'})
        self.assertRaises(exception, _PersonalService.validate_contact, {'/abc': '..'})
        self.assertRaises(exception, _PersonalService.validate_contact, {'abc/': '..'})
        self.assertRaises(exception, _PersonalService.validate_contact, {'..': '..'})
        self.assertRaises(exception, _PersonalService.validate_contact, {'./././abc': '..'})
        self.assertRaises(exception, _PersonalService.validate_contact, {'./abc': '..'})
        self.assertRaises(exception, _PersonalService.validate_contact, {'abc/.': '..'})
        self.assertRaises(exception, _PersonalService.validate_contact, {'abcd./../../../abc': '..'})
        self.assertRaises(exception, _PersonalService.validate_contact, {'abcd./../../..': '..'})

    def test_that_validate_contact_accepts_keys_with_separators(self):
        _PersonalService.validate_contact({'abcd.def.ghij': '..'})
        _PersonalService.validate_contact({'.abcd.def.ghij.': '..'})
        _PersonalService.validate_contact({'abcd/def/ghij': '..'})
        _PersonalService.validate_contact({'abcd.def/ghi.jkl': '..'})

    def test_that_validate_contact_accepts_correct_contact(self):
        contact_infos = {
            'firstname': 'Alice',
            'lastname': 'Bob',
        }

        result = _PersonalService.validate_contact(contact_infos)

        assert_that(result, is_(None))
