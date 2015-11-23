# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2015 Avencall
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

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import equal_to
from hamcrest import empty
from hamcrest import is_
from hamcrest import none
from mock import Mock
from ..xivo_user_plugin import XivoUserPlugin
from xivo_dird import make_result_class

CONFD_CONFIG = {'host': 'xivo.example.com',
                'username': 'admin',
                'password': 'secret',
                'port': 9487,
                'version': '1.1'}
DEFAULT_ARGS = {'config': {'confd_config': CONFD_CONFIG,
                           'name': 'my_test_xivo',
                           'searched_columns': ['firstname', 'lastname']}}
UUID = 'my-xivo-uuid'

SourceResult = make_result_class(DEFAULT_ARGS['config']['name'],
                                 unique_column='id')

CONFD_USER_1 = {
    "agent_id": 42,
    "exten": '666',
    "firstname": "Louis-Jean",
    "id": 226,
    "lastname": "",
    "line_id": 123,
    'userfield': None,
    'description': None,
    "links": [
        {
            "href": "http://localhost:9487/1.1/users/226",
            "rel": "users"
        },
        {
            "href": "http://localhost:9487/1.1/lines/123",
            "rel": "lines"
        }

    ],
    "mobile_phone_number": "5555551234",
    "voicemail_number": "1234",
}

SOURCE_1 = SourceResult(
    {'id': 226,
     'exten': '666',
     'firstname': 'Louis-Jean',
     'lastname': '',
     'userfield': None,
     'description': None,
     'mobile_phone_number': '5555551234',
     'voicemail_number': '1234'},
    xivo_id=UUID,
    agent_id=42,
    user_id=226,
    endpoint_id=123,
)

CONFD_USER_2 = {
    "agent_id": None,
    "exten": '1234',
    "firstname": "Paul",
    "id": 227,
    "lastname": "",
    "line_id": 320,
    'userfield': '555',
    'description': 'here',
    "links": [
        {
            "href": "http://localhost:9487/1.1/users/227",
            "rel": "users"
        },
        {
            "href": "http://localhost:9487/1.1/lines/320",
            "rel": "lines"
        },
    ],
    "mobile_phone_number": "",
    "voicemail_number": None,
}

SOURCE_2 = SourceResult(
    {'id': 227,
     'exten': '1234',
     'firstname': 'Paul',
     'lastname': '',
     'mobile_phone_number': '',
     'userfield': '555',
     'description': 'here',
     'voicemail_number': None},
    xivo_id=UUID,
    user_id=227,
    endpoint_id=320,
)


class _BaseTest(unittest.TestCase):

    def setUp(self):
        self._FakedConfdClient = Mock(return_value=Mock(name='confd_client'))
        self._confd_client = self._FakedConfdClient.return_value
        self._source = XivoUserPlugin(self._FakedConfdClient)


class TestXivoUserBackendSearch(_BaseTest):

    def setUp(self):
        super(TestXivoUserBackendSearch, self).setUp()
        response = {'items': [CONFD_USER_1, CONFD_USER_2]}
        self._confd_client.users.list.return_value = response
        self._source._client = self._confd_client
        self._source._SourceResult = SourceResult
        self._source._uuid = UUID

    def test_search_on_excluded_column(self):
        self._source._searched_columns = ['lastname']

        result = self._source.search(term='paul')

        self._confd_client.users.list.assert_called_once_with(view='directory',
                                                              search='paul')

        assert_that(result, empty())

    def test_search_on_included_column(self):
        self._source._searched_columns = ['firstname', 'lastname']

        result = self._source.search(term='paul')

        self._confd_client.users.list.assert_called_once_with(view='directory',
                                                              search='paul')

        assert_that(result, contains(SOURCE_2))

    def test_first_match(self):
        self._source._first_matched_columns = ['exten']

        result = self._source.first_match('1234')

        self._confd_client.users.list.assert_called_once_with(view='directory',
                                                              search='1234')

        assert_that(result, equal_to(SOURCE_2))

    def test_first_match_return_none_when_no_result(self):
        self._source._first_matched_columns = ['number']

        result = self._source.first_match('12')

        self._confd_client.users.list.assert_called_once_with(view='directory',
                                                              search='12')

        assert_that(result, is_(none()))

    def test_list_with_unknown_id(self):
        result = self._source.list(unique_ids=['42'])

        self._confd_client.users.list.assert_called_once_with(view='directory')

        assert_that(result, empty())

    def test_list_with_known_id(self):
        result = self._source.list(unique_ids=['226'])

        self._confd_client.users.list.assert_called_once_with(view='directory')

        assert_that(result, contains(SOURCE_1))

    def test_list_with_empty_list(self):
        result = self._source.list(unique_ids=[])

        self._confd_client.users.list.assert_called_once_with(view='directory')

        assert_that(result, contains())

    def test_fetch_entries_when_client_does_not_return_list(self):
        self._confd_client.users.list.side_effect = Exception()

        result = self._source._fetch_entries()

        assert_that(result, empty())

    def test_fetch_entries_when_client_does_not_return_uuid(self):
        self._source._uuid = None
        self._confd_client.infos.side_effect = Exception()

        result = self._source._fetch_entries()

        assert_that(result, empty())


class TestXivoUserBackendInitialisation(_BaseTest):

    def setUp(self):
        super(TestXivoUserBackendInitialisation, self).setUp()
        self._confd_client.infos.return_value = {'uuid': UUID}

    def test_load_searched_columns(self):
        self._source.load(DEFAULT_ARGS)

        assert_that(self._source._searched_columns,
                    equal_to(DEFAULT_ARGS['config']['searched_columns']))

    def test_load_name(self):
        self._source.load(DEFAULT_ARGS)

        assert_that(self._source.name,
                    equal_to(DEFAULT_ARGS['config']['name']))

    def test_load_client(self):
        self._source.load(DEFAULT_ARGS)

        confd_config = DEFAULT_ARGS['config']['confd_config']
        self._FakedConfdClient.assert_called_once_with(**confd_config)

        assert_that(self._source._client, self._confd_client)

    def test_make_source_result_from_entry(self):
        entry = CONFD_USER_2
        SourceResult = make_result_class('my_test_xivo')

        self._source._SourceResult = SourceResult

        result = self._source._source_result_from_entry(entry, UUID)

        expected = SourceResult({'id': 227,
                                 'exten': '1234',
                                 'firstname': 'Paul',
                                 'lastname': '',
                                 'mobile_phone_number': '',
                                 'voicemail_number': None,
                                 'userfield': '555',
                                 'description': 'here'},
                                xivo_id=UUID, user_id=227, endpoint_id=320)

        assert_that(result, equal_to(expected))
