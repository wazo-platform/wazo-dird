# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from typing import NamedTuple

from wazo_dird_client import Client as DirdClient

from wazo_dird.database.queries.personal import PersonalContactCRUD
from wazo_dird.database.queries.phonebook import (
    PhonebookContactCRUD,
    PhonebookCRUD,
    PhonebookKey,
)
from wazo_dird.plugins.config_service.plugin import (
    CONFERENCE_SOURCE_BODY,
    GOOGLE_SOURCE_BODY,
    OFFICE_365_SOURCE_BODY,
    PERSONAL_SOURCE_BODY,
    WAZO_SOURCE_BODY,
)

from .helpers.base import BaseDirdIntegrationTest
from .helpers.config import new_null_config
from .helpers.constants import MAIN_TENANT, MAIN_USER_UUID, VALID_TOKEN_MAIN_TENANT

_CONTACT_COUNT = 25_000
_PERSONAL_CONTACT_COUNT = 1_000
_NUMBER_BASE = 1_000_000_000
_MOBILE_BASE = 33_600_000_000

# Must match the static confd fixtures under
# integration_tests/assets/confd_data/asset.graphql_load/.
_WAZO_PROOF_EXTEN = '2000'
_WAZO_PROOF_REVERSE = 'PbxUser0000 Wazo0000'

_CONFERENCE_PROOF_EXTEN = '4000'
_CONFERENCE_PROOF_REVERSE = 'Conference 00'

_LOW_EXTEN_COUNTS = (1, 2, 3, 4, 5, 20)

_MOCK_AUTH = {
    'host': 'auth',
    'port': 9497,
    'https': False,
    'prefix': None,
    'username': 'graphql-load-test',
    'password': 'graphql-load-test',
}
_MOCK_CONFD = {
    'host': 'confd',
    'port': 9486,
    'https': False,
    'prefix': None,
}
# No external-auth seeded, so google/office365 always fail fast with a 404.
_MOCK_OAUTH_AUTH = {
    'host': 'auth',
    'port': 9497,
    'https': False,
    'prefix': None,
}

_DISPLAY_COLUMNS = [
    {'title': 'Firstname', 'field': 'firstname'},
    {'title': 'Lastname', 'field': 'lastname'},
    {'title': 'Number', 'field': 'number'},
    {'title': 'Mobile', 'field': 'mobile'},
    {'title': 'Email', 'field': 'email'},
]


def _graphql_query(profile: str, extens: list[str]) -> dict:
    return {
        'query': '''
            query($profile: String, $extens: [String]) {
                me {
                    contacts(profile: $profile, extens: $extens) {
                        edges {
                            node { firstname lastname wazoReverse }
                        }
                    }
                }
            }
        ''',
        'variables': {'profile': profile, 'extens': extens},
    }


class LatencyStats(NamedTuple):
    min: float
    max: float
    avg: float
    p50: float
    p95: float
    p99: float


def latency_stats(latencies: list[float]) -> LatencyStats:
    times = sorted(latencies)
    n = len(times)
    return LatencyStats(
        min=times[0],
        max=times[-1],
        avg=sum(times) / n,
        p50=times[int(n * 0.50) - 1],
        p95=times[int(n * 0.95) - 1],
        p99=times[int(n * 0.99) - 1],
    )


def concurrent_p50_budget(num_extens: int) -> float:
    # need to be generous to tolerate CI variability
    # and scale with query size
    return 3.0 + 0.2 * num_extens


class _GraphQLLoadBase(BaseDirdIntegrationTest):
    asset = 'graphql_load'
    config_factory = new_null_config

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.stack = ExitStack()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.stack.close()
        super().tearDownClass()


class TestGraphQLReverseLookupDefaultProfileLoad(_GraphQLLoadBase):
    """
    Load scenario matching the production "default" profile: a 25k-contact
    phonebook alongside all 5 sources auto-created for a real tenant
    (personal, wazo, conference, google, office365), instead of 8 duplicate
    phonebook sources fanning out to the same data. wazo/conference are
    backed by a confd mock; google/office365 are never linked to an
    account, so they always fail fast — the common production default.
    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

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

        personal_crud = PersonalContactCRUD(cls.Session)
        personal_contacts = personal_crud.create_personal_contacts(
            MAIN_TENANT,
            MAIN_USER_UUID,
            [
                {
                    'firstname': f'Contact{i:05d}',
                    'lastname': f'McContact{i:05d}',
                    'number': str(_NUMBER_BASE + i),
                    'mobile': str(_MOBILE_BASE + i),
                    'email': f'contact{i:05d}@example.com',
                }
                for i in range(_PERSONAL_CONTACT_COUNT)
            ],
        )
        assert len(personal_contacts) == _PERSONAL_CONTACT_COUNT
        cls.stack.callback(personal_crud.delete_all_personal_contacts, MAIN_USER_UUID)

        client = cls.get_client(VALID_TOKEN_MAIN_TENANT)

        phonebook_source = client.phonebook_source.create(
            {
                'name': 'graphql-load-test-phonebook',
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
        cls.stack.callback(client.phonebook_source.delete, phonebook_source['uuid'])

        personal_source = client.personal_source.create(
            {**PERSONAL_SOURCE_BODY, 'name': 'graphql-load-test-personal'}
        )
        cls.stack.callback(client.personal_source.delete, personal_source['uuid'])

        # auto-create bodies, with auth/confd pointed at this asset's mock
        wazo_source = client.wazo_source.create(
            {
                **WAZO_SOURCE_BODY,
                'name': 'graphql-load-test-wazo',
                'auth': _MOCK_AUTH,
                'confd': _MOCK_CONFD,
            }
        )
        cls.stack.callback(client.wazo_source.delete, wazo_source['uuid'])

        conference_source = client.conference_source.create(
            {
                **CONFERENCE_SOURCE_BODY,
                'name': 'graphql-load-test-conference',
                'auth': _MOCK_AUTH,
                'confd': _MOCK_CONFD,
            }
        )
        cls.stack.callback(client.conference_source.delete, conference_source['uuid'])

        # auto-created but never linked to an account (see _MOCK_OAUTH_AUTH)
        google_source = client.backends.create_source(
            'google',
            {
                **GOOGLE_SOURCE_BODY,
                'name': 'graphql-load-test-google',
                'auth': _MOCK_OAUTH_AUTH,
            },
        )
        cls.stack.callback(
            client.backends.delete_source, 'google', google_source['uuid']
        )

        office365_source = client.backends.create_source(
            'office365',
            {
                **OFFICE_365_SOURCE_BODY,
                'name': 'graphql-load-test-office365',
                'auth': _MOCK_OAUTH_AUTH,
            },
        )
        cls.stack.callback(
            client.backends.delete_source, 'office365', office365_source['uuid']
        )

        sources = [
            phonebook_source,
            personal_source,
            wazo_source,
            conference_source,
            google_source,
            office365_source,
        ]

        display = client.displays.create(
            {'name': 'graphql-load-test-display', 'columns': _DISPLAY_COLUMNS}
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

    def test_wazo_source_resolves(self) -> None:
        """A confd-backed exten resolves via the wazo source.

        Proves the confd mock is live: without it, the wazo source would
        fail to load (or every lookup against it would time out) and this
        would be indistinguishable from a source that was never queried.
        """
        response = self.dird.graphql.query(
            _graphql_query('default', [_WAZO_PROOF_EXTEN])
        )
        assert 'errors' not in response, f'GraphQL errors: {response.get("errors")}'
        edges = response['data']['me']['contacts']['edges']
        assert len(edges) == 1, f'Expected 1 result, got {len(edges)}'
        node = edges[0]['node']
        assert node is not None, 'wazo source failed to resolve a confd-backed exten'
        assert node['wazoReverse'] == _WAZO_PROOF_REVERSE

    def test_conference_source_resolves(self) -> None:
        """A confd-backed conference exten resolves via the conference source.

        Same rationale as test_wazo_source_resolves: proves the conference
        source is live rather than silently absent or timing out.
        """
        response = self.dird.graphql.query(
            _graphql_query('default', [_CONFERENCE_PROOF_EXTEN])
        )
        assert 'errors' not in response, f'GraphQL errors: {response.get("errors")}'
        edges = response['data']['me']['contacts']['edges']
        assert len(edges) == 1, f'Expected 1 result, got {len(edges)}'
        node = edges[0]['node']
        assert (
            node is not None
        ), 'conference source failed to resolve a confd-backed exten'
        assert node['wazoReverse'] == _CONFERENCE_PROOF_REVERSE

    def test_unconfigured_google_office365_do_not_break_lookup(self) -> None:
        """google/office365 always fail (no external auth configured), but
        that shouldn't error the request or block other sources' matches.
        """
        exten = str(_NUMBER_BASE)
        response = self.dird.graphql.query(_graphql_query('default', [exten]))
        assert 'errors' not in response, f'GraphQL errors: {response.get("errors")}'
        edges = response['data']['me']['contacts']['edges']
        assert len(edges) == 1, f'Expected 1 result, got {len(edges)}'
        assert edges[0]['node'] is not None, 'phonebook match missing'

    def test_single_request(self) -> None:
        """Single GraphQL reverse lookup at 1-5 and 20 extensions against the
        25k-contact phonebook (the bulk of the fan-out; personal/wazo/
        conference contribute no matches for these extens and are pure
        overhead, as in production).

        The 1.0s threshold is the same one already used for 20 extens; it
        hasn't been independently tuned for the lower counts.
        """
        for num_extens in _LOW_EXTEN_COUNTS:
            with self.subTest(num_extens=num_extens):
                step = _CONTACT_COUNT // num_extens
                extens = [str(_NUMBER_BASE + i * step) for i in range(num_extens)]

                t0 = time.monotonic()
                response = self.dird.graphql.query(_graphql_query('default', extens))
                elapsed = time.monotonic() - t0

                print(
                    f'load[single]: {num_extens} extens / 25k contacts → {elapsed:.2f}s'
                )

                assert (
                    'errors' not in response
                ), f'GraphQL errors: {response.get("errors")}'
                edges = response['data']['me']['contacts']['edges']
                assert (
                    len(edges) == num_extens
                ), f'Expected {num_extens} results, got {len(edges)}'
                missing = [extens[i] for i, e in enumerate(edges) if e['node'] is None]
                assert not missing, f'Extens not found in phonebook: {missing}'
                assert elapsed < 1.0, f'Single request {elapsed:.2f}s exceeds 1s'

    def test_concurrent_50_users(self) -> None:
        """50 concurrent GraphQL requests at 1-5 and 20 extensions each,
        against 25k contacts.

        50 users × 6 sources per request compete for the ThreadPoolExecutor
        in _ReverseService, reproducing production queuing at the
        executor_workers size configured for this asset.
        """
        num_users = 50

        for num_extens in _LOW_EXTEN_COUNTS:
            with self.subTest(num_extens=num_extens):

                def run_query(
                    user_idx: int, num_extens: int = num_extens
                ) -> tuple[float, dict]:
                    client = DirdClient(
                        self.host,
                        self.port,
                        prefix=None,
                        https=False,
                        token=VALID_TOKEN_MAIN_TENANT,
                        timeout=120,
                    )
                    # each user queries a distinct phonebook slice
                    offset = (user_idx * num_extens * 50) % _CONTACT_COUNT
                    extens = [
                        str(_NUMBER_BASE + (offset + j * 50) % _CONTACT_COUNT)
                        for j in range(num_extens)
                    ]
                    t0 = time.monotonic()
                    response = client.graphql.query(_graphql_query('default', extens))
                    return time.monotonic() - t0, response

                with ThreadPoolExecutor(max_workers=num_users) as pool:
                    results = list(pool.map(run_query, range(num_users)))

                stats = latency_stats([t for t, _ in results])
                print(
                    f'load[concurrent {num_users} users, {num_extens} extens, '
                    f'6 sources / 25k contacts]: min={stats.min:.2f}s '
                    f'avg={stats.avg:.2f}s p50={stats.p50:.2f}s p95={stats.p95:.2f}s '
                    f'p99={stats.p99:.2f}s max={stats.max:.2f}s'
                )

                all_errors = [
                    err
                    for _, resp in results
                    if 'errors' in resp
                    for err in resp['errors']
                ]
                assert not all_errors, f'GraphQL errors: {all_errors}'

                for _, resp in results:
                    edges = resp['data']['me']['contacts']['edges']
                    assert (
                        len(edges) == num_extens
                    ), f'Expected {num_extens} results, got {len(edges)}'
                    null_nodes = [i for i, e in enumerate(edges) if e['node'] is None]
                    assert (
                        not null_nodes
                    ), f'Null nodes at indices {null_nodes} (timeout?)'

                budget = concurrent_p50_budget(num_extens)
                assert stats.p50 < budget, (
                    f'p50 latency {stats.p50:.2f}s exceeds budget {budget:.2f}s '
                    f'({num_extens} extens, {num_users} users)'
                )


class TestGraphQLReverseLookupPersonalLoad(_GraphQLLoadBase):
    """
    Load scenario for the personal backend: a single user with 1k personal
    contacts firing concurrent reverse lookups. Reproduces the worst-case for
    the personal backend (one user with many contacts, many in-flight calls).
    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        personal_crud = PersonalContactCRUD(cls.Session)
        contacts = personal_crud.create_personal_contacts(
            MAIN_TENANT,
            MAIN_USER_UUID,
            [
                {
                    'firstname': f'Contact{i:05d}',
                    'lastname': f'McContact{i:05d}',
                    'number': str(_NUMBER_BASE + i),
                    'mobile': str(_MOBILE_BASE + i),
                    'email': f'contact{i:05d}@example.com',
                }
                for i in range(_PERSONAL_CONTACT_COUNT)
            ],
        )
        assert len(contacts) == _PERSONAL_CONTACT_COUNT

        def _cleanup_personal_contacts() -> None:
            personal_crud.delete_all_personal_contacts(MAIN_USER_UUID)

        cls.stack.callback(_cleanup_personal_contacts)

        client = cls.get_client(VALID_TOKEN_MAIN_TENANT)

        source = client.personal_source.create(
            {
                'name': 'graphql-load-test-personal-source',
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
        cls.stack.callback(client.personal_source.delete, source['uuid'])

        display = client.displays.create(
            {'name': 'graphql-load-test-personal-display', 'columns': _DISPLAY_COLUMNS}
        )
        cls.stack.callback(client.displays.delete, display['uuid'])

        profile = client.profiles.create(
            {
                'name': 'personal',
                'display': display,
                'services': {'reverse': {'sources': [source]}},
            }
        )
        cls.stack.callback(client.profiles.delete, profile['uuid'])

    def test_single_request_20_extens(self) -> None:
        """Single GraphQL reverse lookup: 20 extensions against 1k personal contacts."""
        step = _PERSONAL_CONTACT_COUNT // 20
        extens = [str(_NUMBER_BASE + i * step) for i in range(20)]

        t0 = time.monotonic()
        response = self.dird.graphql.query(_graphql_query('personal', extens))
        elapsed = time.monotonic() - t0

        print(f'load[single, personal]: 20 extens / 1k contacts → {elapsed:.2f}s')

        assert 'errors' not in response, f'GraphQL errors: {response.get("errors")}'
        edges = response['data']['me']['contacts']['edges']
        assert len(edges) == 20, f'Expected 20 results, got {len(edges)}'
        missing = [extens[i] for i, e in enumerate(edges) if e['node'] is None]
        assert not missing, f'Extens not found in personal contacts: {missing}'
        assert elapsed < 1.0, f'Single request {elapsed:.2f}s exceeds 1s'

    def test_concurrent_50_users_20_extens(self) -> None:
        """50 concurrent GraphQL requests by the same user, 20 extens each.

        All requests share MAIN_USER_UUID — represents one heavily-active user
        whose client (e.g. softphone refreshing call history) issues many
        concurrent reverse lookups against their 1k personal contacts.
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
            offset = (user_idx * num_extens) % _PERSONAL_CONTACT_COUNT
            extens = [
                str(_NUMBER_BASE + (offset + j) % _PERSONAL_CONTACT_COUNT)
                for j in range(num_extens)
            ]
            t0 = time.monotonic()
            response = client.graphql.query(_graphql_query('personal', extens))
            return time.monotonic() - t0, response

        with ThreadPoolExecutor(max_workers=num_users) as pool:
            results = list(pool.map(run_query, range(num_users)))

        stats = latency_stats([t for t, _ in results])
        print(
            f'load[concurrent {num_users} users, {num_extens} extens, '
            f'personal / 1k contacts]: min={stats.min:.2f}s avg={stats.avg:.2f}s '
            f'p50={stats.p50:.2f}s p95={stats.p95:.2f}s p99={stats.p99:.2f}s '
            f'max={stats.max:.2f}s'
        )

        all_errors = [
            err for _, resp in results if 'errors' in resp for err in resp['errors']
        ]
        assert not all_errors, f'GraphQL errors: {all_errors}'

        for _, resp in results:
            edges = resp['data']['me']['contacts']['edges']
            assert (
                len(edges) == num_extens
            ), f'Expected {num_extens} results, got {len(edges)}'
            null_nodes = [i for i, e in enumerate(edges) if e['node'] is None]
            assert not null_nodes, f'Null nodes at indices {null_nodes} (timeout?)'

        budget = concurrent_p50_budget(num_extens)
        assert stats.p50 < budget, (
            f'p50 latency {stats.p50:.2f}s exceeds budget {budget:.2f}s '
            f'({num_extens} extens, {num_users} users)'
        )
