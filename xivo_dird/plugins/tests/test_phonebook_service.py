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

import unittest

from hamcrest import (assert_that, calling, equal_to, raises)
from mock import Mock, sentinel as s

from xivo_dird import database
from xivo_dird.core.exception import InvalidPhonebookException

from ..phonebook_service import (PhonebookServicePlugin as Plugin,
                                 _PhonebookService as Service)


class TestPhonebookServicePlugin(unittest.TestCase):

    def setUp(self):
        self.args = {'config': {'db_uri': s.db_uri}}

    def test_that_loading_without_a_proper_config_raises(self):
        plugin = Plugin()

        assert_that(calling(plugin.load).with_args({}),
                    raises(ValueError))
        assert_that(calling(plugin.load).with_args({'config': {}}),
                    raises(ValueError))


class TestPhonebookServicePhonebookAPI(unittest.TestCase):

    def setUp(self):
        self.phonebook_crud = Mock(database.PhonebookCRUD)
        self.contact_crud = Mock(database.PhonebookContactCRUD)
        self.service = Service(self.phonebook_crud,
                               self.contact_crud)

    def test_list_phonebook(self):
        result = self.service.list_phonebook(s.tenant)

        assert_that(result, equal_to(self.phonebook_crud.list.return_value))

    def test_create_phonebook(self):
        body = {'name': 'a name'}

        result = self.service.create_phonebook(s.tenant, body)

        self.phonebook_crud.create.assert_called_once_with(s.tenant, body)
        assert_that(result, equal_to(self.phonebook_crud.create.return_value))

    def test_count_phonebook(self):
        result = self.service.count_phonebook(s.tenant, param1=s.param1)

        self.phonebook_crud.count.assert_called_once_with(s.tenant, param1=s.param1)
        assert_that(result, equal_to(self.phonebook_crud.count.return_value))

    def test_that_create_with_no_name_raises(self):
        bodies = [{}, {'name': ''}, {'name': None}]
        for body in bodies:
            assert_that(calling(self.service.create_phonebook).with_args(s.tenant, body),
                        raises(InvalidPhonebookException))

    def test_edit_phonebook(self):
        body = {'name': 'foobar'}

        result = self.service.edit_phonebook(s.tenant, s.phonebook_id, body)

        self.phonebook_crud.edit.assert_called_once_with(s.tenant, s.phonebook_id, body)
        assert_that(result, equal_to(self.phonebook_crud.edit.return_value))

    def test_that_edit_with_no_name_raises(self):
        bodies = [{}, {'name': ''}, {'name': None}]
        for body in bodies:
            assert_that(calling(self.service.edit_phonebook).with_args(s.tenant, s.phonebook_id, body),
                        raises(InvalidPhonebookException))

    def test_delete_phonebook(self):
        self.service.delete_phonebook(s.tenant, s.phonebook_id)

        self.phonebook_crud.delete.assert_called_once_with(s.tenant, s.phonebook_id)

    def test_get_phonebook(self):
        result = self.service.get_phonebook(s.tenant, s.phonebook_id)

        assert_that(result, equal_to(self.phonebook_crud.get.return_value))
        self.phonebook_crud.get.assert_called_once_with(s.tenant, s.phonebook_id)


class TestPhonebookServiceContactAPI(unittest.TestCase):

    def setUp(self):
        self.phonebook_crud = Mock(database.PhonebookCRUD)
        self.contact_crud = Mock(database.PhonebookContactCRUD)
        self.service = Service(self.phonebook_crud,
                               self.contact_crud)

    def test_count_contact(self):
        result = self.service.count_contact(s.tenant, s.phonebook_id)

        assert_that(result, equal_to(self.contact_crud.count.return_value))
        self.contact_crud.count.assert_called_once_with(s.tenant, s.phonebook_id)

    def test_count_contact_with_a_search_param(self):
        result = self.service.count_contact(s.tenant, s.phonebook_id, search=s.search)

        assert_that(result, equal_to(self.contact_crud.count.return_value))
        self.contact_crud.count.assert_called_once_with(s.tenant, s.phonebook_id, search=s.search)

    def test_create_contact(self):
        result = self.service.create_contact(s.tenant, s.phonebook_id, s.contact_info)

        assert_that(result, equal_to(self.contact_crud.create.return_value))
        self.contact_crud.create.assert_called_once_with(s.tenant, s.phonebook_id, s.contact_info)

    def test_edit_contact(self):
        result = self.service.edit_contact(s.tenant, s.phonebook_id, s.contact_uuid, s.contact_info)

        assert_that(result, equal_to(self.contact_crud.edit.return_value))
        self.contact_crud.edit.assert_called_once_with(s.tenant, s.phonebook_id,
                                                       s.contact_uuid, s.contact_info)

    def test_delete_contact(self):
        result = self.service.delete_contact(s.tenant, s.phonebook_id, s.contact_uuid)

        assert_that(result, equal_to(self.contact_crud.delete.return_value))
        self.contact_crud.delete.assert_called_once_with(s.tenant, s.phonebook_id, s.contact_uuid)

    def test_get_contact(self):
        result = self.service.get_contact(s.tenant, s.phonebook_id, s.contact_uuid)

        assert_that(result, equal_to(self.contact_crud.get.return_value))
        self.contact_crud.get.assert_called_once_with(s.tenant, s.phonebook_id, s.contact_uuid)
