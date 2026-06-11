# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Stress-test for GraphQL reverse lookups against a real Wazo stack.
# Simulates application behaviour: each virtual user picks 0-35 extensions
# at random from the configured phonebook range and fires a single GraphQL
# reverse lookup, then waits between requests.
#
# Requirements:  pip install locust
#
# Usage:
#   export WAZO_TOKEN=<token>   WAZO_TENANT=<tenant-uuid>
#   locust -f locustfile.py -H https://<stack-host> \
#     --headless --users 50 --spawn-rate 5 --run-time 60s
#
# Optional env vars:
#   WAZO_PROFILE        profile name for the reverse lookup (default: default)
#   NUMBER_BASE         lowest phone number in the phonebook  (default: 1000000000)
#   MOBILE_BASE         lowest mobile number in the phonebook (default: 33600000000)
#   PHONEBOOK_COUNT     number of contacts in the phonebook   (default: 25000)
#   P95_THRESHOLD_MS    fail if p95 exceeds this value in ms  (default: 4000)
#   FAIL_RATIO_PCT      fail if error rate exceeds this %     (default: 5)

import json
import logging
import os
import random

from locust import FastHttpUser, between, events, task
from locust.env import Environment

_TOKEN = os.environ['WAZO_TOKEN']
_TENANT = os.getenv('WAZO_TENANT', '')
_PROFILE = os.getenv('WAZO_PROFILE', 'default')
_NUMBER_BASE = int(os.getenv('NUMBER_BASE', '1000000000'))
_MOBILE_BASE = int(os.getenv('MOBILE_BASE', '33600000000'))
_PHONEBOOK_COUNT = int(os.getenv('PHONEBOOK_COUNT', '25000'))
_P95_THRESHOLD_MS = int(os.getenv('P95_THRESHOLD_MS', '4000'))
_FAIL_RATIO_PCT = float(os.getenv('FAIL_RATIO_PCT', '5'))


class GraphQLReverseLookupUser(FastHttpUser):
    """
    Simulates one application instance resolving call-history entries via
    GraphQL reverse lookup.  Each task picks 1-35 extensions (skip on 0
    to match real app idle behaviour) drawn from the synthetic phonebook.
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
            '/0.1/graphql',
            name='graphql_reverse_lookup',
            headers=headers,
            json={'query': query},
            catch_response=True,
            timeout=10,
        ) as response:
            if response.status_code >= 500:
                response.failure(response.text)
            elif response.status_code >= 400:
                response.failure(f'{response.status_code}: {response.text[:200]}')
            else:
                body = response.json()
                if 'errors' in body:
                    response.failure(str(body['errors'])[:200])
                else:
                    response.success()


@events.test_start.add_listener
def on_start(environment: Environment, **kw: dict) -> None:
    logging.info(
        'target: %s  profile: %s  phonebook: %d contacts',
        environment.host,
        _PROFILE,
        _PHONEBOOK_COUNT,
    )


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
