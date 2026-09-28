# Copyright 2014-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from typing import Any, cast
from unittest.mock import Mock, call, patch

from hamcrest import (
    assert_that,
    calling,
    contains_exactly,
    empty,
    equal_to,
    has_entries,
    is_,
    none,
    raises,
)
from requests import HTTPError, RequestException

from wazo_dird import make_result_class
from wazo_dird.exception import InvalidConfigError, SourceUnavailable
from wazo_dird.plugins.base_plugins import SourcePluginDependencies

from ..plugin import WazoUserPlugin


def _http_error(status_code: int) -> RequestException:
    return HTTPError(response=Mock(status_code=status_code))


TENANT_UUID = '02153e33-4b59-4a9f-8cd1-7e917b306e1d'
AUTH_CONFIG = {
    'host': 'xivo.example.com',
    'backend': 'wazo_user',
    'username': 'foo',
    'password': 'bar',
}
CONFD_CONFIG = {'host': 'xivo.example.com', 'port': 9486, 'version': '1.1'}
DEFAULT_ARGS = {
    'config': {
        'uuid': 'ae086548-2d36-4367-8914-8dfcd8645ca7',
        'backend': 'wazo',
        'tenant_uuid': TENANT_UUID,
        'confd': CONFD_CONFIG,
        'auth': AUTH_CONFIG,
        'name': 'my_test_xivo',
        'searched_columns': ['firstname', 'lastname', 'full_name'],
    }
}
UUID = 'my-xivo-uuid'

UUID_1 = '55abf77c-5744-44a0-9c36-34da29f647cb'
UUID_2 = '22f51ae2-296d-4340-a7d5-3567ae66df73'
UUID_3 = '3b8e6b2c-4f1a-4c7e-9a2f-0f4a1d6c8e55'

SourceResult = make_result_class(
    cast(str, DEFAULT_ARGS['config']['backend']),
    cast(str, DEFAULT_ARGS['config']['name']),
    unique_column='uuid',
)

CONFD_USER_1 = {
    "agent_id": 42,
    "exten": '666',
    "firstname": "Louis-Jean",
    "lastname": "",
    "id": 226,
    'uuid': UUID_1,
    "line_id": 123,
    'userfield': None,
    'description': None,
    "links": [
        {"href": "http://localhost:9487/1.1/users/226", "rel": "users"},
        {"href": "http://localhost:9487/1.1/lines/123", "rel": "lines"},
    ],
    "email": "louis-jean@aucun.com",
    "mobile_phone_number": "5555551234",
    "voicemail_number": "1234",
}

SOURCE_1 = SourceResult(
    {
        'id': 226,
        'uuid': UUID_1,
        'exten': '666',
        'firstname': 'Louis-Jean',
        'lastname': '',
        'full_name': "Louis-Jean",
        'userfield': None,
        'description': None,
        'email': 'louis-jean@aucun.com',
        'mobile_phone_number': '5555551234',
        'voicemail_number': '1234',
    },
    xivo_id=UUID,
    agent_id=42,
    user_id=226,
    user_uuid=UUID_1,
    endpoint_id=123,
)

CONFD_USER_2 = {
    "agent_id": None,
    "exten": '1234',
    "firstname": "Paul",
    "id": 227,
    'uuid': UUID_2,
    "lastname": "àccent",
    "line_id": 320,
    'userfield': '555',
    'description': 'here',
    "links": [
        {"href": "http://localhost:9487/1.1/users/227", "rel": "users"},
        {"href": "http://localhost:9487/1.1/lines/320", "rel": "lines"},
    ],
    'email': '',
    "mobile_phone_number": "",
    "voicemail_number": None,
}

SOURCE_2 = SourceResult(
    {
        'id': 227,
        'uuid': UUID_2,
        'exten': '1234',
        'firstname': 'Paul',
        'lastname': 'àccent',
        'full_name': 'Paul àccent',
        'email': '',
        'mobile_phone_number': '',
        'userfield': '555',
        'description': 'here',
        'voicemail_number': None,
    },
    xivo_id=UUID,
    user_id=227,
    user_uuid=UUID_2,
    endpoint_id=320,
)


CONFD_USER_3: dict[str, Any] = {
    "agent_id": None,
    "exten": '777',
    "firstname": "Collide",
    "lastname": "McCollide",
    "id": 228,
    'uuid': UUID_3,
    "line_id": 321,
    'userfield': None,
    'description': None,
    "links": [],
    'email': '',
    # the same value as CONFD_USER_1's exten, so the two columns disagree
    "mobile_phone_number": "666",
    "voicemail_number": None,
}

SOURCE_3 = SourceResult(
    {
        'id': 228,
        'uuid': UUID_3,
        'exten': '777',
        'firstname': 'Collide',
        'lastname': 'McCollide',
        'full_name': 'Collide McCollide',
        'email': '',
        'mobile_phone_number': '666',
        'userfield': None,
        'description': None,
        'voicemail_number': None,
    },
    xivo_id=UUID,
    user_id=228,
    user_uuid=UUID_3,
    endpoint_id=321,
)


class _BaseTest(unittest.TestCase):
    def setUp(self):
        self._source = WazoUserPlugin()
        # the source manager always names a source before loading it
        self._source.name = cast(str, DEFAULT_ARGS['config']['name'])
        self._confd_client = Mock()
        self._source._client = self._confd_client


def _confd_users_list(**params: Any) -> dict[str, Any]:
    """Answer like confd: `uuid`, `exten` and `mobile_phone_number` are exact
    filters, `search` is not.
    """
    items: list[dict[str, Any]] = [CONFD_USER_1, CONFD_USER_2, CONFD_USER_3]
    for field in ('uuid', 'exten', 'mobile_phone_number'):
        wanted = params.get(field)
        if wanted is None:
            continue
        keep = set(wanted.split(','))
        items = [user for user in items if user[field] in keep]
    return {'items': items, 'total': len(items)}


class TestWazoUserBackendLoad(_BaseTest):
    def _load(self, first_matched_columns):
        config = dict(cast(dict, DEFAULT_ARGS['config']))
        config['first_matched_columns'] = first_matched_columns
        with patch('wazo_dird.plugins.wazo_user_backend.plugin.registry'):
            self._source.load(
                cast(SourcePluginDependencies, {'config': config}),
            )

    def test_load_accepts_a_column_confd_can_match_exactly(self):
        self._load(['exten', 'mobile_phone_number'])

        assert_that(
            self._source._first_matched_columns,
            contains_exactly('exten', 'mobile_phone_number'),
        )

    def test_load_refuses_a_column_confd_cannot_match_exactly(self):
        assert_that(
            calling(self._load).with_args(['number']),
            raises(InvalidConfigError),
        )


class TestWazoUserBackendSearch(_BaseTest):
    def setUp(self):
        super().setUp()
        self._confd_client.users.list.side_effect = _confd_users_list
        self._source._client = self._confd_client
        self._source._SourceResult = SourceResult
        self._source._uuid = UUID

    def test_search_on_excluded_column(self):
        self._source._searched_columns = ['lastname']

        result = self._source.search(term='paul')

        self._confd_client.users.list.assert_called_once_with(
            recurse=True, view='directory', search='paul'
        )

        assert_that(result, empty())

    def test_search_on_included_column(self):
        self._source._searched_columns = ['firstname', 'lastname', 'full_name']

        search_terms = ['paul', 'paul ', 'paul àccent', 'Paul À']
        for term in search_terms:
            result = self._source.search(term=term)

            self._confd_client.users.list.assert_called_with(
                recurse=True, view='directory', search=term
            )

            assert_that(result, contains_exactly(SOURCE_2))

    def test_that_search_uses_extra_search_params(self):
        config = dict(DEFAULT_ARGS)
        config['config']['extra_search_params'] = {'context': 'inside'}

        with patch('wazo_dird.plugins.wazo_user_backend.plugin.registry') as registry:
            self._source.load(cast(SourcePluginDependencies, DEFAULT_ARGS))

            self._source.search(term='paul')

            client = registry.get.return_value
            client.users.list.assert_called_once_with(
                recurse=True, view='directory', search='paul', context='inside'
            )

    def test_search_with_no_accent(self):
        self._source._searched_columns = ['firstname', 'lastname']

        result = self._source.search(term='accent')

        self._confd_client.users.list.assert_called_once_with(
            recurse=True, view='directory', search='accent'
        )

        assert_that(result, contains_exactly(SOURCE_2))

    def test_search_with_wrong_accent(self):
        self._source._searched_columns = ['firstname', 'lastname']

        result = self._source.search(term='accént')

        self._confd_client.users.list.assert_called_once_with(
            recurse=True, view='directory', search='accént'
        )

        assert_that(result, contains_exactly(SOURCE_2))

    def test_first_match_uses_the_exact_filter(self):
        self._source._first_matched_columns = ['exten']

        result = self._source.first_match('1234')

        self._confd_client.users.list.assert_called_once_with(
            recurse=True, view='directory', exten='1234'
        )

        assert_that(result, equal_to(SOURCE_2))

    def test_first_match_stops_at_the_first_column_that_matches(self):
        self._source._first_matched_columns = ['exten', 'mobile_phone_number']

        result = self._source.first_match('1234')

        self._confd_client.users.list.assert_called_once_with(
            recurse=True, view='directory', exten='1234'
        )

        assert_that(result, equal_to(SOURCE_2))

    def test_first_match_tries_every_supported_column(self):
        self._source._first_matched_columns = ['exten', 'mobile_phone_number']

        result = self._source.first_match('5555551234')

        self._confd_client.users.list.assert_has_calls(
            [
                call(recurse=True, view='directory', exten='5555551234'),
                call(recurse=True, view='directory', mobile_phone_number='5555551234'),
            ]
        )

        assert_that(result, equal_to(SOURCE_1))

    def test_first_match_and_match_all_agree_when_columns_disagree(self):
        self._source._first_matched_columns = ['exten', 'mobile_phone_number']

        first = self._source.first_match('666')
        every = self._source.match_all(['666'])

        assert_that(first, equal_to(SOURCE_1))
        assert_that(every, has_entries({'666': SOURCE_1}))

    def test_an_empty_term_never_reaches_confd(self):
        self._source._first_matched_columns = ['exten', 'mobile_phone_number']

        assert_that(self._source.first_match(''), is_(none()))
        assert_that(self._source.match_all(['']), equal_to({}))

        self._confd_client.users.list.assert_not_called()

    def test_first_match_return_none_when_no_result(self):
        self._source._first_matched_columns = ['exten']

        result = self._source.first_match('12')

        self._confd_client.users.list.assert_called_once_with(
            recurse=True, view='directory', exten='12'
        )

        assert_that(result, is_(none()))

    def test_match_all(self):
        self._source._first_matched_columns = ['exten']

        result = self._source.match_all(['1234', '5678'])

        self._confd_client.users.list.assert_called_once_with(
            recurse=True, view='directory', exten='1234,5678'
        )

        assert_that(result, has_entries({'1234': SOURCE_2}))

    def test_match_all_when_no_result(self):
        self._source._first_matched_columns = ['exten']

        result = self._source.match_all(['12'])

        self._confd_client.users.list.assert_called_once_with(
            recurse=True, view='directory', exten='12'
        )

        assert_that(result, has_entries({}))

    def test_match_all_uses_the_exact_filters_even_for_a_single_term(self):
        self._source._first_matched_columns = ['exten', 'mobile_phone_number']

        self._source.match_all(['12'])

        self._confd_client.users.list.assert_has_calls(
            [
                call(recurse=True, view='directory', exten='12'),
                call(recurse=True, view='directory', mobile_phone_number='12'),
            ]
        )

    def test_list_with_unknown_uuid(self):
        unknown_uuid = '11111111-1111-4111-8111-111111111111'

        result = self._source.list(unique_ids=[unknown_uuid])

        self._confd_client.users.list.assert_called_once_with(
            recurse=True, view='directory', uuid=unknown_uuid
        )

        assert_that(result, empty())

    def test_list_with_known_uuid(self):
        result = self._source.list(unique_ids=[UUID_1])

        self._confd_client.users.list.assert_called_once_with(
            recurse=True, view='directory', uuid=UUID_1
        )

        assert_that(result, contains_exactly(SOURCE_1))

    def test_list_asks_confd_for_the_wanted_uuids_only(self):
        result = self._source.list(unique_ids=[UUID_1, UUID_2])

        self._confd_client.users.list.assert_called_once_with(
            recurse=True, view='directory', uuid=f'{UUID_1},{UUID_2}'
        )

        assert_that(result, contains_exactly(SOURCE_1, SOURCE_2))

    def test_list_splits_large_requests_in_batches(self):
        uuids = [f'{i:08d}-1111-4111-8111-111111111111' for i in range(21)]

        self._source.list(unique_ids=uuids)

        assert_that(self._confd_client.users.list.call_count, equal_to(2))
        first_call, second_call = self._confd_client.users.list.call_args_list
        assert_that(
            first_call,
            equal_to(call(recurse=True, view='directory', uuid=','.join(uuids[:20]))),
        )
        assert_that(
            second_call, equal_to(call(recurse=True, view='directory', uuid=uuids[20]))
        )

    def test_canonical_unique_id_of_a_uuid_confd_knows_is_that_uuid(self):
        self._confd_client.users.get.return_value = CONFD_USER_1

        result = self._source.canonical_unique_id(UUID_1)

        self._confd_client.users.get.assert_called_once_with(UUID_1)
        assert_that(result, equal_to(UUID_1))

    def test_canonical_unique_id_translates_a_confd_id_during_the_transition(self):
        # the write path stores the uuid, so the database keeps one form
        self._confd_client.users.get.return_value = CONFD_USER_1

        result = self._source.canonical_unique_id('226')

        self._confd_client.users.get.assert_called_once_with('226')
        assert_that(result, equal_to(UUID_1))

    def test_canonical_unique_id_of_a_user_confd_does_not_know_is_none(self):
        self._confd_client.users.get.side_effect = _http_error(404)

        assert_that(self._source.canonical_unique_id(UUID_1), is_(none()))

    def test_canonical_unique_id_of_a_malformed_id_does_not_ask_confd(self):
        for unique_id in ['', 'not-an-id', '226-a', 'null']:
            assert_that(self._source.canonical_unique_id(unique_id), is_(none()))

        self._confd_client.users.get.assert_not_called()

    def test_canonical_unique_id_aborts_when_confd_is_unreachable(self):
        # an unknown user is a 400, but an unreachable confd must not be
        self._confd_client.users.get.side_effect = RequestException()

        self.assertRaises(SourceUnavailable, self._source.canonical_unique_id, UUID_1)

    def test_translate_unique_id_of_a_uuid_does_not_ask_confd(self):
        result = self._source.translate_unique_id(UUID_1)

        self._confd_client.users.get.assert_not_called()
        assert_that(result, equal_to(UUID_1))

    def test_translate_unique_id_resolves_a_confd_id_during_the_transition(self):
        self._confd_client.users.get.return_value = CONFD_USER_1

        result = self._source.translate_unique_id('226')

        self._confd_client.users.get.assert_called_once_with('226')
        assert_that(result, equal_to(UUID_1))

    def test_translate_unique_id_keeps_a_confd_id_confd_does_not_know(self):
        # a wrong id deletes nothing, so there is nothing to refuse
        self._confd_client.users.get.side_effect = _http_error(404)

        assert_that(self._source.translate_unique_id('226'), equal_to('226'))

    def test_translate_unique_id_aborts_when_confd_is_unreachable(self):
        self._confd_client.users.get.side_effect = RequestException()

        self.assertRaises(SourceUnavailable, self._source.translate_unique_id, '226')

    def test_list_with_empty_list_does_not_reach_confd(self):
        result = self._source.list(unique_ids=[])

        self._confd_client.users.list.assert_not_called()

        assert_that(result, contains_exactly())

    def test_fetch_entries_when_client_does_not_return_list(self):
        self._confd_client.users.list.side_effect = RequestException()

        result = self._source._fetch_entries()

        assert_that(result, empty())

    def test_fetch_entries_when_client_does_not_return_uuid(self):
        self._source._uuid = None
        self._confd_client.infos.side_effect = RequestException()

        result = self._source._fetch_entries()

        assert_that(result, empty())
