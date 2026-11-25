# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from typing import cast
from unittest.mock import Mock, patch

from hamcrest import (
    assert_that,
    calling,
    contains_exactly,
    equal_to,
    has_entries,
    raises,
)
from requests import ConnectionError

from wazo_dird.exception import SourceListError

from ..plugin import CSVWSPlugin, Dependencies

LIST_URL = 'http://example.com:8000/list'


def _source(**extra):
    config = {
        'lookup_url': 'http://example.com:8000/ws',
        'name': 'my-ws-source',
        'timeout': 3,
        **extra,
    }
    source = CSVWSPlugin()
    source.load(cast(Dependencies, {'config': config}))
    source.name = 'my-ws-source'
    return source


@patch('wazo_dird.plugins.csv_ws_backend.plugin.requests')
class TestCSVWSListAll(unittest.TestCase):
    def test_list_all_returns_every_row_of_the_list_url(self, requests):
        requests.get.return_value = Mock(
            status_code=200, text='id,name\n1,Alice\n2,Bob\n'
        )
        source = _source(list_url=LIST_URL)

        results = source.list_all()

        requests.get.assert_called_once_with(LIST_URL, timeout=3, verify=True)
        assert_that(
            [r.fields for r in results],
            contains_exactly(has_entries(name='Alice'), has_entries(name='Bob')),
        )

    def test_list_all_without_a_list_url_lists_nothing(self, requests):
        source = _source()

        assert_that(source.list_all(), equal_to([]))
        requests.get.assert_not_called()

    def test_list_all_raises_when_the_list_url_is_unreachable(self, requests):
        requests.get.side_effect = ConnectionError()
        source = _source(list_url=LIST_URL)

        assert_that(calling(source.list_all), raises(SourceListError))

    def test_list_all_raises_when_the_list_url_does_not_answer_200(self, requests):
        requests.get.return_value = Mock(status_code=503, text='')
        source = _source(list_url=LIST_URL)

        assert_that(calling(source.list_all), raises(SourceListError))
