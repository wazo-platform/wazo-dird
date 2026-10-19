# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import cast
from unittest.mock import patch

import pytest

from wazo_dird.config import Config
from wazo_dird.http_server import CoreRestApi


@pytest.fixture
def rest_api():
    config = {
        'auth': {},
        'rest_api': {
            'listen': '127.0.0.1',
            'port': 9489,
            'min_threads': 1,
            'max_threads': 1,
            'certificate': None,
            'private_key': None,
            'cors': {'enabled': False},
        },
    }
    return CoreRestApi(cast(Config, config))


def test_stop_before_run_does_not_raise_and_sets_the_tombstone(rest_api):
    rest_api.stop()

    assert rest_api._stopped.is_set()


@patch('wazo_dird.http_server.wsgi')
def test_run_after_stop_does_not_start_the_server(wsgi, rest_api):
    rest_api.stop()
    rest_api.run()

    wsgi.DynamicWSGIServer.return_value.start.assert_not_called()


@patch('wazo_dird.http_server.wsgi')
def test_stop_after_run_stops_the_server(wsgi, rest_api):
    rest_api.run()
    rest_api.stop()

    wsgi.DynamicWSGIServer.return_value.stop.assert_called_once_with()
