# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from flask_restful import Api, Resource

from wazo_dird.http_cache import (
    CACHE_CONTROL_CONFIG_KEY,
    add_cache_control,
    sanitized_max_ages,
)


class Cacheable(Resource):
    cache_control_key = 'cacheable'

    def get(self) -> dict[str, Any]:
        return {'hello': 'world'}

    def post(self) -> tuple[dict[str, Any], int]:
        return {'hello': 'world'}, 201


class Failing(Resource):
    cache_control_key = 'cacheable'

    def get(self) -> tuple[dict[str, Any], int]:
        return {'reason': ['nope']}, 503


class Disabled(Resource):
    cache_control_key = 'disabled'

    def get(self) -> dict[str, Any]:
        return {'hello': 'world'}


class Unregistered(Resource):
    cache_control_key = 'unregistered'

    def get(self) -> dict[str, Any]:
        return {'hello': 'world'}


class Undeclared(Resource):
    def get(self) -> dict[str, Any]:
        return {'hello': 'world'}


@pytest.fixture
def client() -> FlaskClient:
    app = Flask(__name__)
    api = Api(app)
    api.add_resource(Cacheable, '/cacheable')
    api.add_resource(Failing, '/failing')
    api.add_resource(Disabled, '/disabled')
    api.add_resource(Unregistered, '/unregistered')
    api.add_resource(Undeclared, '/undeclared')
    app.config[CACHE_CONTROL_CONFIG_KEY] = {'cacheable': 3600, 'disabled': 0}
    app.after_request(add_cache_control)
    return app.test_client()


def test_a_configured_resource_is_marked_private_and_fresh(client):
    response = client.get('/cacheable')

    assert response.headers['Cache-Control'] == 'private, max-age=3600'


def test_a_resource_configured_to_zero_gets_no_header(client):
    response = client.get('/disabled')

    assert 'Cache-Control' not in response.headers


def test_a_resource_absent_from_the_configuration_gets_no_header(client):
    response = client.get('/unregistered')

    assert 'Cache-Control' not in response.headers


def test_a_resource_declaring_no_key_gets_no_header(client):
    response = client.get('/undeclared')

    assert 'Cache-Control' not in response.headers


def test_a_non_get_method_gets_no_header(client):
    response = client.post('/cacheable')

    assert 'Cache-Control' not in response.headers


def test_a_non_200_response_gets_no_header(client):
    response = client.get('/failing')

    assert 'Cache-Control' not in response.headers


def test_an_unrouted_request_gets_no_header(client):
    response = client.get('/unknown')

    assert 'Cache-Control' not in response.headers


@pytest.mark.parametrize(
    'value',
    [-1, 'an hour', 3.5, True, None],
)
def test_sanitized_max_ages_drops_invalid_values(value):
    assert sanitized_max_ages({'profile_sources': value}) == {}


def test_sanitized_max_ages_keeps_valid_values():
    assert sanitized_max_ages({'profile_sources': 3600, 'other': 0}) == {
        'profile_sources': 3600,
        'other': 0,
    }
