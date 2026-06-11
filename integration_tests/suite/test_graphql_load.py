# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack

from wazo_dird_client import Client as DirdClient

from wazo_dird.database.queries.phonebook import (
    PhonebookContactCRUD,
    PhonebookCRUD,
    PhonebookKey,
)

from .helpers.base import BaseDirdIntegrationTest
from .helpers.config import new_null_config
from .helpers.constants import MAIN_TENANT, VALID_TOKEN_MAIN_TENANT

logger = logging.getLogger(__name__)

_CONTACT_COUNT = 25_000
_NUMBER_BASE = 1_000_000_000
_MOBILE_BASE = 33_600_000_000


class TestGraphQLReverseLookupLoad(BaseDirdIntegrationTest):
    """
    Load scenario reproducing Cultura production conditions:
    25k-contact phonebook, GraphQL reverse lookup with 15-20 extensions.

    Timing is logged for performance baseline; tests gate on correctness only.
    """

    asset = 'graphql_load'
    config_factory = new_null_config

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.dird = DirdClient(
            cls.host,
            cls.port,
            prefix=None,
            https=False,
            token=VALID_TOKEN_MAIN_TENANT,
            timeout=10,
        )
        cls.stack = ExitStack()

        phonebook_crud = PhonebookCRUD(cls.Session)
        contact_crud = PhonebookContactCRUD(cls.Session)

        phonebook = phonebook_crud.create(
            MAIN_TENANT,
            {'name': 'graphql-load-test', 'description': '25k contacts load scenario'},
        )
        cls.stack.callback(
            phonebook_crud.delete, None, PhonebookKey(uuid=phonebook['uuid'])
        )

        contacts, errors = contact_crud.create_many(
            [MAIN_TENANT],
            PhonebookKey(uuid=phonebook['uuid']),
            [
                {
                    'firstname': f'Contact{i:05d}',
                    'lastname': f'McContact{i:05d}',
                    'number': str(_NUMBER_BASE + i),
                    'mobile': str(_MOBILE_BASE + i),
                    'email': f'contact{i:05d}@example.com',
                }
                for i in range(_CONTACT_COUNT)
            ],
        )
        assert not errors, f'Contact creation errors: {errors}'
        assert len(contacts) == _CONTACT_COUNT

        client = cls.get_client(VALID_TOKEN_MAIN_TENANT)

        # Create 8 sources pointing to the same phonebook, matching production
        # fan-out (Google, O365, wazo-users + multiple phonebooks).
        # Each request submits one future per source to the shared 10-worker
        # ThreadPoolExecutor in _ReverseService — the key bottleneck.
        _NUM_SOURCES = 8
        sources = []
        for i in range(_NUM_SOURCES):
            source = client.phonebook_source.create(
                {
                    'name': f'graphql-load-test-source-{i}',
                    'phonebook_uuid': phonebook['uuid'],
                    'searched_columns': [
                        'firstname',
                        'lastname',
                        'number',
                        'mobile',
                        'email',
                    ],
                    'first_matched_columns': ['number', 'mobile'],
                    'format_columns': {'reverse': '{firstname} {lastname}'},
                }
            )
            cls.stack.callback(client.phonebook_source.delete, source['uuid'])
            sources.append(source)

        display = client.displays.create(
            {
                'name': 'graphql-load-test-display',
                'columns': [
                    {'title': 'Firstname', 'field': 'firstname'},
                    {'title': 'Lastname', 'field': 'lastname'},
                    {'title': 'Number', 'field': 'number'},
                    {'title': 'Mobile', 'field': 'mobile'},
                    {'title': 'Email', 'field': 'email'},
                ],
            }
        )
        cls.stack.callback(client.displays.delete, display['uuid'])

        profile = client.profiles.create(
            {
                'name': 'default',
                'display': display,
                'services': {'reverse': {'sources': sources}},
            }
        )
        cls.stack.callback(client.profiles.delete, profile['uuid'])

    @classmethod
    def tearDownClass(cls) -> None:
        cls.stack.close()
        super().tearDownClass()

    @staticmethod
    def _graphql_query(extens: list[str]) -> dict:
        return {
            'query': '''
            {
                me {
                    contacts(profile: "default", extens: $extens) {
                        edges {
                            node {
                                firstname
                                lastname
                                wazoReverse
                            }
                        }
                    }
                }
            }
            '''.replace(
                '$extens', json.dumps(extens)
            ),
        }

    def test_single_request_20_extens(self) -> None:
        """Single GraphQL reverse lookup: 20 extensions against 25k-contact phonebook."""
        step = _CONTACT_COUNT // 20
        extens = [str(_NUMBER_BASE + i * step) for i in range(20)]

        t0 = time.monotonic()
        response = self.dird.graphql.query(self._graphql_query(extens))
        elapsed = time.monotonic() - t0

        logger.info('load[single]: 20 extens / 25k contacts → %.2fs', elapsed)

        assert 'errors' not in response, f'GraphQL errors: {response.get("errors")}'
        edges = response['data']['me']['contacts']['edges']
        assert len(edges) == 20, f'Expected 20 results, got {len(edges)}'
        missing = [extens[i] for i, e in enumerate(edges) if e['node'] is None]
        assert not missing, f'Extens not found in phonebook: {missing}'
        assert elapsed < 1.0, f'Single request {elapsed:.2f}s exceeds 1s'

    def test_concurrent_50_users_20_extens(self) -> None:
        """50 concurrent GraphQL requests, 20 extensions each, against 25k contacts.

        50 users × 8 sources = 400 futures competing for the 10-worker
        ThreadPoolExecutor in _ReverseService, reproducing production queuing.
        """
        num_users = 50
        num_extens = 20

        def run_query(user_idx: int) -> tuple[float, dict]:
            client = DirdClient(
                self.host,
                self.port,
                prefix=None,
                https=False,
                token=VALID_TOKEN_MAIN_TENANT,
                timeout=120,
            )
            # Each user queries a distinct non-overlapping slice of the phonebook
            offset = (user_idx * num_extens * 50) % _CONTACT_COUNT
            extens = [
                str(_NUMBER_BASE + (offset + j * 50) % _CONTACT_COUNT)
                for j in range(num_extens)
            ]
            t0 = time.monotonic()
            response = client.graphql.query(self._graphql_query(extens))
            return time.monotonic() - t0, response

        with ThreadPoolExecutor(max_workers=num_users) as pool:
            results = list(pool.map(run_query, range(num_users)))

        times = sorted(t for t, _ in results)
        p50 = times[num_users // 2]
        p95 = times[int(num_users * 0.95) - 1]
        logger.info(
            'load[concurrent %d users, %d extens, 8 sources / 25k contacts]: '
            'min=%.2fs p50=%.2fs p95=%.2fs max=%.2fs',
            num_users,
            num_extens,
            times[0],
            p50,
            p95,
            times[-1],
        )

        all_errors = [
            err for _, resp in results if 'errors' in resp for err in resp['errors']
        ]
        assert not all_errors, f'GraphQL errors: {all_errors}'

        for _elapsed, resp in results:
            edges = resp['data']['me']['contacts']['edges']
            assert (
                len(edges) == num_extens
            ), f'Expected {num_extens} results, got {len(edges)}'

        assert p95 < 4.0, f'p95 latency {p95:.2f}s exceeds 4s'
