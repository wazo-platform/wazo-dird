# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Stress-test for wazo-dird directory services against a real Wazo stack.
# Three scenarios, each exercising one service's ThreadPoolExecutor fan-out
# (one future per profile source):
#
#   GraphQLReverseLookupUser  GraphQL reverse lookup (reverse_service pool)
#   LookupUser                REST lookup by term     (lookup_service pool)
#   FavoritesUser             REST favorites listing  (favorites_service pool)
#
# All scenarios assume a synthetic phonebook and a profile with several sources
# already exist on the target stack (see contribs/create_synthetic_phonebook.sh
# and contribs/create_phonebook_source.sh). FavoritesUser additionally requires
# favorites to be seeded for the test user (see contribs/create_favorites.sh).
#
# Requirements:  pip install locust
#
# Usage (run ONE scenario at a time to isolate a single service's pool):
#   export WAZO_LOGIN=root WAZO_PASSWORD=secret WAZO_TENANT=<tenant-uuid>
#   locust -f locustfile.py GraphQLReverseLookupUser -H https://<stack-host> \
#     --headless --users 50 --spawn-rate 5 --run-time 60s
#   locust -f locustfile.py LookupUser    -H https://<stack-host> --headless ...
#   locust -f locustfile.py FavoritesUser -H https://<stack-host> --headless ...
#
# Required env vars:
#   WAZO_LOGIN          wazo-auth username
#   WAZO_PASSWORD       wazo-auth password
#   WAZO_TENANT         tenant UUID sent as Wazo-Tenant header
#
# Optional env vars:
#   WAZO_AUTH_HOST      auth base URL (default: WAZO_HOST/api/auth)
#   WAZO_PROFILE        profile name for the queries (default: default)
#   NUMBER_BASE         lowest phone number in the phonebook  (default: 1000000000)
#   MOBILE_BASE         lowest mobile number in the phonebook (default: 33600000000)
#   PHONEBOOK_COUNT     number of contacts in the phonebook   (default: 25000)
#   P95_THRESHOLD_MS    fail if p95 exceeds this value in ms  (default: 4000)
#   FAIL_RATIO_PCT      fail if error rate exceeds this %     (default: 5)

from __future__ import annotations

import base64
import json
import logging
import os
import random
import ssl
import urllib.request
from typing import TYPE_CHECKING

from locust import FastHttpUser, between, events, task
from locust.env import Environment

if TYPE_CHECKING:
    from locust.contrib.fasthttp import ResponseContextManager

_LOGIN = os.environ['WAZO_LOGIN']
_PASSWORD = os.environ['WAZO_PASSWORD']
_TENANT = os.getenv('WAZO_TENANT', '')
_PROFILE = os.getenv('WAZO_PROFILE', 'default')
_NUMBER_BASE = int(os.getenv('NUMBER_BASE', '1000000000'))
_MOBILE_BASE = int(os.getenv('MOBILE_BASE', '33600000000'))
_PHONEBOOK_COUNT = int(os.getenv('PHONEBOOK_COUNT', '25000'))
_P95_THRESHOLD_MS = int(os.getenv('P95_THRESHOLD_MS', '4000'))
_FAIL_RATIO_PCT = float(os.getenv('FAIL_RATIO_PCT', '5'))

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def _create_token(host: str) -> str:
    auth_host = os.getenv('WAZO_AUTH_HOST', f'{host}/api/auth')
    credentials = base64.b64encode(f'{_LOGIN}:{_PASSWORD}'.encode()).decode()
    req = urllib.request.Request(
        f'{auth_host}/0.1/token',
        data=json.dumps({'expiration': 600}).encode(),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Basic {credentials}',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, context=_SSL_CTX) as resp:
        data = json.loads(resp.read())
    return data['data']['token']


def _delete_token(host: str, token: str) -> None:
    auth_host = os.getenv('WAZO_AUTH_HOST', f'{host}/api/auth')
    req = urllib.request.Request(f'{auth_host}/0.1/token/{token}', method='DELETE')
    try:
        urllib.request.urlopen(req, context=_SSL_CTX).close()
    except urllib.error.URLError as e:
        logging.warning('failed to delete token: %s', e)


class GraphQLReverseLookupUser(FastHttpUser):
    """
    Simulates one application instance resolving call-history entries via
    GraphQL reverse lookup.  Each task picks 0-35 extensions drawn from the
    synthetic phonebook. All virtual users share a single token created at
    test_start, so authentication latency is excluded from the stats.
    """

    wait_time = between(0.5, 3.0)

    @task
    def reverse_lookup(self) -> None:
        n_extens = random.randint(0, 35)
        indices = random.sample(range(_PHONEBOOK_COUNT), n_extens) if n_extens else []
        # Mix number and mobile fields to exercise both first_matched_columns
        extens = [
            str(_NUMBER_BASE + i) if random.random() < 0.5 else str(_MOBILE_BASE + i)
            for i in indices
        ]

        query = (
            '{ me { contacts(profile: "'
            + _PROFILE
            + '", extens: '
            + json.dumps(extens)
            + ') { edges { node { firstname lastname wazoReverse } } } } }'
        )

        headers = {'X-Auth-Token': _TOKEN, 'Content-Type': 'application/json'}
        if _TENANT:
            headers['Wazo-Tenant'] = _TENANT

        with self.client.post(
            '/api/dird/0.1/graphql',
            name='graphql_reverse_lookup',
            headers=headers,
            json={'query': query},
            catch_response=True,
            timeout=_P95_THRESHOLD_MS / 1000,
        ) as response:
            if not response.status_code:
                response.failure('timeout or connection error')
            else:
                response.raise_for_status()
                body = response.json()
                if 'errors' in body:
                    response.failure(str(body['errors'])[:200])
                else:
                    response.success()


def _query_headers() -> dict[str, str]:
    headers = {'X-Auth-Token': _TOKEN}
    if _TENANT:
        headers['Wazo-Tenant'] = _TENANT
    return headers


def _check_rest_response(response: ResponseContextManager) -> None:
    if not response.status_code:
        response.failure('timeout or connection error')
    else:
        response.raise_for_status()
        response.success()


class LookupUser(FastHttpUser):
    """
    Simulates contact search: each task searches the firstname of a random
    synthetic contact, fanning out one future per profile source in the
    lookup_service ThreadPoolExecutor.
    """

    wait_time = between(0.5, 3.0)

    @task
    def lookup(self) -> None:
        term = f'Contact{random.randrange(_PHONEBOOK_COUNT):05d}'
        with self.client.get(
            f'/api/dird/0.1/directories/lookup/{_PROFILE}',
            name='lookup',
            headers=_query_headers(),
            params={'term': term},
            catch_response=True,
            timeout=_P95_THRESHOLD_MS / 1000,
        ) as response:
            _check_rest_response(response)


class FavoritesUser(FastHttpUser):
    """
    Simulates favorites listing: each task lists the test user's favorites,
    fanning out one future per source holding a favorite in the
    favorites_service ThreadPoolExecutor.

    Favorites must be seeded beforehand (see contribs/create_favorites.sh);
    with no favorites the listing still succeeds but exercises no fan-out.
    """

    wait_time = between(0.5, 3.0)

    @task
    def favorites(self) -> None:
        with self.client.get(
            f'/api/dird/0.1/directories/favorites/{_PROFILE}',
            name='favorites',
            headers=_query_headers(),
            catch_response=True,
            timeout=_P95_THRESHOLD_MS / 1000,
        ) as response:
            _check_rest_response(response)


_TOKEN = ''


@events.test_start.add_listener
def on_test_start(environment: Environment, **kw: dict) -> None:
    global _TOKEN
    _TOKEN = _create_token(environment.host)
    logging.info(
        'target: %s  profile: %s  phonebook: %d contacts',
        environment.host,
        _PROFILE,
        _PHONEBOOK_COUNT,
    )


@events.test_stop.add_listener
def on_test_stop(environment: Environment, **kw: dict) -> None:
    if _TOKEN:
        _delete_token(environment.host, _TOKEN)


@events.quitting.add_listener
def on_quit(environment: Environment, **kw: dict) -> None:
    stats = environment.stats.total
    p95 = stats.get_response_time_percentile(0.95)
    fail_pct = stats.fail_ratio * 100
    logging.info(
        'results: rps=%.1f  p50=%.0fms  p95=%.0fms  p99=%.0fms  failures=%.1f%%',
        stats.current_rps,
        stats.get_response_time_percentile(0.50),
        p95,
        stats.get_response_time_percentile(0.99),
        fail_pct,
    )
    if fail_pct > _FAIL_RATIO_PCT:
        logging.error('FAIL: failure rate %.1f%% > %.1f%%', fail_pct, _FAIL_RATIO_PCT)
        environment.process_exit_code = 1
    elif p95 > _P95_THRESHOLD_MS:
        logging.error('FAIL: p95 %.0fms > %dms', p95, _P95_THRESHOLD_MS)
        environment.process_exit_code = 1
    else:
        logging.info('PASS')
        environment.process_exit_code = 0
