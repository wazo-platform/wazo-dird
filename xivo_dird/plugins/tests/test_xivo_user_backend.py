# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Avencall
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
from hamcrest import contains_inanyorder
from hamcrest import equal_to
from hamcrest import empty
from mock import Mock
from mock import sentinel
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
                                 unique_columns=['id'])

CONFD_USER_1 = {
    "agent_id": 42,
    "exten": '666',
    "firstname": "Louis-Jean",
    "id": 226,
    "lastname": "",
    "line_id": 123,
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
    "mobile_phone_number": "5555551234"
}

SOURCE_1 = SourceResult(
    {'id': 226,
     'exten': '666',
     'firstname': 'Louis-Jean',
     'lastname': '',
     'mobile_phone_number': '5555551234'},
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
    "mobile_phone_number": ""
}

SOURCE_2 = SourceResult(
    {'id': 227,
     'exten': '1234',
     'firstname': 'Paul',
     'lastname': '',
     'mobile_phone_number': ''},
    xivo_id=UUID,
    user_id=227,
    endpoint_id=320,
)


class _BaseTest(unittest.TestCase):

    def setUp(self):
        self._FakedConfdClient = Mock(return_value=Mock())
        self._confd_client = self._FakedConfdClient.return_value
        self._source = XivoUserPlugin(self._FakedConfdClient)


class TestXivoUserBackendSearch(_BaseTest):

    def setUp(self):
        super(TestXivoUserBackendSearch, self).setUp()
        self._source._entries = [SOURCE_1, SOURCE_2]

    def test_search_on_excluded_column(self):
        self._source._searched_columns = ['lastname']

        result = self._source.search(term='paul')

        assert_that(result, empty())

    def test_search_on_included_column(self):
        self._source._searched_columns = ['firstname', 'lastname']

        result = self._source.search(term='paul')

        assert_that(result, contains(SOURCE_2))

    def test_list_with_unknown_id(self):
        result = self._source.list(unique_ids=[(42,)])

        assert_that(result, empty())

    def test_list_with_known_id(self):
        result = self._source.list(unique_ids=[(226,)])

        assert_that(result, contains(SOURCE_1))


class TestXivoUserBackendInitialisation(_BaseTest):

    def test_load(self):
        self._source._fetch_content = Mock()

        self._source.load(DEFAULT_ARGS)

        self._source._fetch_content.assert_called_once_with()

        assert_that(self._source._searched_columns,
                    equal_to(DEFAULT_ARGS['config']['searched_columns']))

    def test_fetch_uuid(self):
        self._confd_client.infos.return_value = {'uuid': sentinel.uuid}
        self._source._confd_config = CONFD_CONFIG

        result = self._source._fetch_uuid()

        self._confd_client.infos.assert_called_once_with()
        assert_that(result, equal_to(sentinel.uuid))

    def test_fetch_users(self):
        confd_result = {
            "items": [
                CONFD_USER_1,
                CONFD_USER_2,
            ],
            'total': 2,
        }
        self._source._confd_config = CONFD_CONFIG
        self._confd_client.users.list.return_value = confd_result
        self._source._fetch_uuid = Mock(return_value={'uuid': 'test'})

        result = self._source._fetch_users()

        assert_that(result, contains_inanyorder(confd_result['items'][0],
                                                confd_result['items'][1]))

    def test_make_source_result_from_entry(self):
        entry = CONFD_USER_2
        SourceResult = make_result_class('my_test_xivo')

        self._source._SourceResult = SourceResult
        self._source._uuid = UUID

        result = self._source._source_result_from_entry(entry)

        expected = SourceResult({'id': 227,
                                 'exten': '1234',
                                 'firstname': 'Paul',
                                 'lastname': '',
                                 'mobile_phone_number': ''},
                                xivo_id=UUID, user_id=227, endpoint_id=320)

        assert_that(result, equal_to(expected))

    def test_refresh_content(self):
        self._source._fetch_uuid = Mock(return_value=UUID)
        self._source._fetch_users = Mock(return_value=[CONFD_USER_1, CONFD_USER_2])
        self._source._SourceResult = SourceResult

        self._source._fetch_content()

        self._source._fetch_uuid.assert_called_once_with()
        self._source._fetch_users.assert_called_once_with()

        assert_that(self._source._entries, contains_inanyorder(SOURCE_1, SOURCE_2))
