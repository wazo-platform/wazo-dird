# -*- coding: utf-8 -*-
# Copyright (C) 2015-2016 Avencall
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

from hamcrest import assert_that
from hamcrest import equal_to
from hamcrest import has_item
from hamcrest import has_property
from mock import Mock
from unittest import TestCase
from uuid import uuid4

from xivo_dird.core import database

from ..personal_backend import PersonalBackend

SOME_UUID = str(uuid4())
CONTACT_1 = {'id': str(uuid4()),
             'firstname': 'Foo'}
CONTACT_2 = {'firstname': 'Bar'}


class TestPersonalBackend(TestCase):

    def setUp(self):
        self._source = PersonalBackend()
        self._search_engine = Mock(database.PersonalContactSearchEngine)
        self._source.load({'config': {'name': 'personal'}}, search_engine=self._search_engine)

    def test_that_list_calls_list_on_the_search_engine(self):
        ids = ['1', '2']
        self._search_engine.list_personal_contacts.return_value = [CONTACT_1, CONTACT_2]

        self._source.list(ids, {'token_infos': {'token': 'valid-token',
                                                'xivo_user_uuid': SOME_UUID}})

        self._search_engine.list_personal_contacts.assert_called_once_with(SOME_UUID, ids)

    def test_that_list_sets_attribute_personal_and_deletable(self):
        self._search_engine.list_personal_contacts.return_value = [CONTACT_1]

        result = self._source.list(['1'], {'token_infos': {'token': 'valid-token',
                                                           'xivo_user_uuid': SOME_UUID}})

        assert_that(result, has_item(has_property('is_personal', True)))
        assert_that(result, has_item(has_property('is_deletable', True)))

    def test_that_search_calls_find_personal_contacts(self):
        self._search_engine.find_personal_contacts.return_value = [CONTACT_1]

        self._source.search('alice', {'token': 'valid-token',
                                      'xivo_user_uuid': SOME_UUID})

        self._search_engine.find_personal_contacts.assert_called_once_with(SOME_UUID, 'alice')

    def test_that_first_match_calls_find_first_personal_contact(self):
        self._search_engine.find_first_personal_contact.return_value = [CONTACT_1]

        result = self._source.first_match('555', {'token': 'valid-token',
                                                  'xivo_user_uuid': SOME_UUID})

        self._search_engine.find_first_personal_contact.assert_called_once_with(SOME_UUID, '555')
        assert_that(result.fields, equal_to(CONTACT_1))

    def test_that_first_match_return_none_if_no_match(self):
        self._search_engine.find_first_personal_contact.return_value = []

        result = self._source.first_match('555', {'token': 'valid-token',
                                                  'xivo_user_uuid': SOME_UUID})

        self._search_engine.find_first_personal_contact.assert_called_once_with(SOME_UUID, '555')
        assert_that(result, equal_to(None))
