# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest.mock import Mock

from hamcrest import assert_that, calling, contains_exactly, has_entries, raises
from requests import ConnectionError, HTTPError

from wazo_dird import make_result_class
from wazo_dird.exception import SourceListError

from ..plugin import ConferencePlugin

CONFERENCES = {
    'items': [
        {
            'id': 1,
            'name': 'daily',
            'extensions': [{'exten': '4001'}],
            'incalls': [{'extensions': [{'exten': '5551234'}]}],
        },
        {'id': 2, 'name': 'weekly', 'extensions': [], 'incalls': []},
    ]
}


class TestConferenceListAll(unittest.TestCase):
    def setUp(self):
        self.source = ConferencePlugin()
        self.source.name = 'conferences'
        self.source._client = Mock()
        self.source._SourceResult = make_result_class('conference', 'conferences', 'id')
        self.source._searched_columns = ['name']

    def test_list_all_returns_every_conference(self):
        self.source._client.conferences.list.return_value = CONFERENCES

        results = self.source.list_all()

        assert_that(
            [r.fields for r in results],
            contains_exactly(
                has_entries(id=1, name='daily', extensions=['4001'], incalls=['5551234']),
                has_entries(id=2, name='weekly'),
            ),
        )

    def test_list_all_raises_when_confd_fails(self):
        for error in (HTTPError(response=Mock(status_code=500)), ConnectionError()):
            self.source._client.conferences.list.side_effect = error

            assert_that(calling(self.source.list_all), raises(SourceListError))

    def test_list_all_raises_when_the_client_is_not_initialised(self):
        self.source._client = None

        assert_that(calling(self.source.list_all), raises(SourceListError))

    def test_search_still_swallows_a_confd_failure(self):
        self.source._client.conferences.list.side_effect = HTTPError()

        assert_that(self.source.search('daily'), contains_exactly())
