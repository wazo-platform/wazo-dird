# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import time
from typing import Any

import requests
from hamcrest import (
    assert_that,
    contains_exactly,
    empty,
    equal_to,
    has_length,
    less_than,
    less_than_or_equal_to,
)
from wazo_test_helpers import until

from .helpers.base import BaseDirdIntegrationTest
from .helpers.config import Config

# the ttl of `asset.wazo_user_snapshot.yml`
TTL = 4
SOURCE = 'wazo_snapshot'
UNKNOWN_UUID = '00000000-0000-4000-8000-00000000ffff'
SOURCE_FIELDS = (
    'name',
    'auth',
    'confd',
    'searched_columns',
    'first_matched_columns',
    'format_columns',
)


def new_snapshot_config(Session):
    config = Config(Session)
    config.with_display(
        name='default_display',
        columns=[
            {'title': 'Firstname', 'field': 'firstname'},
            {'title': 'Lastname', 'field': 'lastname'},
            {'title': 'Number', 'field': 'exten'},
        ],
    )
    config.with_source(
        backend='wazo',
        name=SOURCE,
        auth={
            'host': 'auth',
            'username': 'foo',
            'password': 'bar',
            'prefix': None,
            'https': False,
        },
        confd={'host': 'confd', 'port': 9486, 'https': False, 'prefix': None},
        searched_columns=['firstname', 'lastname'],
        first_matched_columns=['exten'],
    )
    config.with_profile(
        name='default',
        display='default_display',
        services={'lookup': {'sources': [SOURCE]}},
    )
    return config


def new_user(index, firstname, lastname, exten):
    return {
        'id': index,
        'uuid': f'00000000-0000-4000-8000-{index:012d}',
        'line_id': index,
        'agent_id': None,
        'firstname': firstname,
        'lastname': lastname,
        'exten': exten,
        'email': '',
        'mobile_phone_number': '',
        'voicemail_number': None,
    }


class BaseSnapshotTest(BaseDirdIntegrationTest):
    """The `wazo` source answers a lookup from a snapshot of the confd users.

    The confd of this asset counts the `GET /1.1/users` requests it gets, so a
    test tells a lookup served from the snapshot (no request) from one that
    asked confd (one request).
    """

    asset = 'wazo_user_snapshot'
    config_factory = new_snapshot_config

    @classmethod
    def confd_url(cls, path):
        return f'http://127.0.0.1:{cls.service_port(9486, "confd")}{path}'

    @classmethod
    def set_confd_users(cls, users, **options):
        response = requests.put(
            cls.confd_url('/_state'), json={'users': users, **options}, timeout=10
        )
        response.raise_for_status()

    @classmethod
    def confd_stats(cls):
        return requests.get(cls.confd_url('/_stats'), timeout=10).json()

    @classmethod
    def confd_is_up(cls):
        try:
            cls.confd_stats()
        except requests.RequestException:
            return False
        return True

    @classmethod
    def users_requests(cls):
        return cls.confd_stats()['users_requests']

    @classmethod
    def expire_snapshot(cls):
        # a lookup that follows loads the users again
        time.sleep(TTL + 1)

    def lastnames(self, term):
        results = self.lookup(term, 'default')['results']
        return sorted(result['column_values'][1] for result in results)

    def source_uuid(self):
        return self.config.created_sources[SOURCE]['uuid']

    def contacts(self, **params):
        return self.client.backends.list_contacts_from_source(
            backend='wazo',
            source_uuid=self.source_uuid(),
            **{'order': 'firstname', 'offset': 0, **params},
        )


class TestWazoUserSnapshot(BaseSnapshotTest):
    def test_a_change_in_confd_shows_after_the_ttl(self):
        """A lookup serves the loaded users until the ttl, then loads them again."""
        self.set_confd_users([new_user(1, 'Alice', 'Before', '1001')])
        self.expire_snapshot()

        assert_that(self.lastnames('alice'), contains_exactly('Before'))
        loaded_at = time.monotonic()
        # a new state clears the request count of the mock
        self.set_confd_users([new_user(1, 'Alice', 'After', '1001')])

        # inside the ttl: the old users, and no request to confd
        assert_that(self.lastnames('alice'), contains_exactly('Before'))
        assert_that(time.monotonic() - loaded_at, less_than(TTL - 1), 'too slow')
        assert_that(self.users_requests(), equal_to(0))

        until.assert_(
            lambda: assert_that(self.lastnames('alice'), contains_exactly('After')),
            timeout=TTL * 3,
        )
        assert_that(self.users_requests(), equal_to(1))

    def test_the_contacts_listing_is_served_from_the_snapshot(self):
        """The listing of the source sends no request to confd inside the ttl."""
        users = [new_user(1, 'Bob', 'Brown', '1002'), new_user(2, 'alice', 'A', '1001')]
        self.set_confd_users(users)
        self.expire_snapshot()
        first = self.contacts()
        # the load is the only request: one, with no limit and no offset
        assert_that(self.confd_stats()['pages'], contains_exactly([None, 0]))
        # a new state clears the request count of the mock
        self.set_confd_users(users)

        assert_that(self.contacts(), equal_to(first))
        # a `uuid` batch is filtered from the snapshot too, though the mock would
        # filter it itself: an unknown uuid matches nothing, a repeated one counts once
        batch = f"{users[1]['uuid']},{UNKNOWN_UUID},{users[1]['uuid']}"
        by_uuid = self.contacts(uuid=batch)
        assert_that(by_uuid['total'], equal_to(1))
        assert_that(
            [contact['firstname'] for contact in by_uuid['items']],
            contains_exactly('alice'),
        )
        assert_that(self.users_requests(), equal_to(0))
        assert_that(first['total'], equal_to(2))
        # sorted as confd sorts: no case, so `alice` is before `Bob`
        assert_that(
            [contact['firstname'] for contact in first['items']],
            contains_exactly('alice', 'Bob'),
        )

    def test_confd_down_keeps_the_loaded_users(self):
        """A failed reload keeps the old users, and a later one picks up the change."""
        self.set_confd_users([new_user(1, 'Alice', 'Before', '1001')])
        self.expire_snapshot()
        assert_that(self.lastnames('alice'), contains_exactly('Before'))

        self.stop_service('confd')
        try:
            time.sleep(TTL + 1)
            assert_that(self.lastnames('alice'), contains_exactly('Before'))
        finally:
            self.start_service('confd')

        until.true(self.confd_is_up, timeout=15)
        self.set_confd_users([new_user(1, 'Alice', 'After', '1001')])
        until.assert_(
            lambda: assert_that(self.lastnames('alice'), contains_exactly('After')),
            timeout=TTL * 4,
        )

    def test_a_source_update_loads_new_users(self):
        """A new version of the source starts from a fresh snapshot, in one request."""
        self.set_confd_users(
            [
                new_user(1, 'Alice', 'Anderson', '1001'),
                new_user(2, 'Bob', 'Brown', '1002'),
            ]
        )
        self.expire_snapshot()
        assert_that(self.lastnames('1001'), empty())
        assert_that(self.lastnames('alice'), contains_exactly('Anderson'))

        source = self.client.wazo_source.get(self.source_uuid())
        body = {field: source[field] for field in SOURCE_FIELDS}
        self.client.wazo_source.edit(
            self.source_uuid(), {**body, 'searched_columns': ['exten']}
        )
        try:
            self.set_confd_users(
                [
                    new_user(1, 'Alice', 'Anderson', '1001'),
                    new_user(2, 'Bob', 'Brown', '1002'),
                ]
            )
            assert_that(self.lastnames('1001'), contains_exactly('Anderson'))
            assert_that(self.lastnames('alice'), empty())
            assert_that(self.users_requests(), equal_to(1))
        finally:
            self.client.wazo_source.edit(self.source_uuid(), body)


class TestWazoUserSnapshotLoad(BaseSnapshotTest):
    def test_the_load_is_one_request_that_serves_lookups_and_listings(self):
        """2,500 users load in one request, with no paging, then answer from memory."""
        users = [
            new_user(i, 'Filler', f'N{i:04d}', str(2000 + i)) for i in range(1, 2500)
        ]
        users.append(new_user(2500, 'Zelda', 'Lastone', '9999'))
        self.set_confd_users(users)
        self.expire_snapshot()

        assert_that(self.lastnames('lastone'), contains_exactly('Lastone'))
        assert_that(self.confd_stats()['pages'], contains_exactly([None, 0]))

        results = self.lookup('filler', 'default')['results']
        entry_ids = {result['relations']['source_entry_id'] for result in results}
        assert_that(results, has_length(2499))
        assert_that(entry_ids, has_length(2499))
        listing = self.contacts(limit=5, offset=0, order='lastname')
        assert_that(listing['total'], equal_to(2500))
        assert_that(
            [contact['lastname'] for contact in listing['items']],
            contains_exactly('Lastone', 'N0001', 'N0002', 'N0003', 'N0004'),
        )
        by_uuid = self.contacts(uuid=users[2499]['uuid'])
        assert_that(by_uuid['total'], equal_to(1))
        assert_that(self.users_requests(), equal_to(1))


# accents, mixed case, ties on the first name, two names that differ by their case,
# and users without a lastname, one of them tied on its first name
ORDERING_USERS = [
    new_user(1, 'Zoe', 'Zimmer', '1001'),
    new_user(2, 'anna', 'Martin', '1002'),
    new_user(3, 'Anna', 'Bernard', '1003'),
    new_user(4, 'Émile', None, '1004'),
    new_user(5, 'Élodie', 'Dubois', '1005'),
    new_user(6, 'Bob', 'Éclair', '1006'),
    new_user(7, 'Bob', 'Abel', '1007'),
    new_user(8, 'bob', 'abel', '1008'),
    new_user(9, 'émile', 'Zed', '1009'),
]


class TestWazoUserSnapshotOrdering(BaseSnapshotTest):
    """With the snapshot the directory answers in the order confd answers.

    The confd of this asset sorts like confd. It stays a model of it: this pins
    that the snapshot and the confd path agree on the model, not on a real confd.
    """

    def sequences(self):
        batch = ','.join(ORDERING_USERS[i]['uuid'] for i in (6, 0, 3, 1, 8))
        listings: dict[str, dict[str, Any]] = {
            'default': {},
            'by lastname': {'order': 'lastname'},
            'by firstname, descending': {'direction': 'desc'},
            'by lastname, descending': {'order': 'lastname', 'direction': 'desc'},
            'first page': {'limit': 4},
            'second page': {'limit': 4, 'offset': 4},
            'last page': {'limit': 4, 'offset': 8},
            'beyond the end': {'offset': 100},
            'a uuid batch': {'uuid': batch},
            'a uuid batch by lastname, descending, paged': {
                'uuid': batch,
                'order': 'lastname',
                'direction': 'desc',
                'limit': 2,
                'offset': 1,
            },
        }
        lookups = {
            term: [
                tuple(result['column_values'])
                for result in self.lookup(term, 'default')['results']
            ]
            for term in ('a', 'e', 'o', 'bob', 'anna', 'z')
        }
        contacts = {}
        for name, params in listings.items():
            result = self.contacts(**params)
            names = [(user['firstname'], user['lastname']) for user in result['items']]
            contacts[name] = (result['total'], names)
        return {'lookups': lookups, 'listings': contacts}

    def test_lookups_and_listings_have_the_same_order_with_and_without_the_cache(self):
        self.set_confd_users(ORDERING_USERS)
        self.expire_snapshot()

        with_cache = self.sequences()
        cache_requests = self.users_requests()
        with self.dird_with_config({'wazo_user_cache_ttl': 0}):
            self.wait_strategy.wait(self.dird)
            without_cache = self.sequences()

        # the first run used the snapshot: far fewer requests than lookups and listings
        assert_that(cache_requests, less_than_or_equal_to(3))
        assert_that(with_cache, equal_to(without_cache))
        # sanity: no case, no accents, and the users without a lastname last
        by_lastname = with_cache['listings']['by lastname'][1]
        assert_that(by_lastname[0], equal_to(('Bob', 'Abel')))
        assert_that(by_lastname[-1], equal_to(('Émile', None)))


class TestWazoUserSnapshotDisabled(BaseSnapshotTest):
    def test_a_ttl_of_zero_asks_confd_for_each_lookup(self):
        """With `wazo_user_cache_ttl: 0` each lookup sends its own request."""
        self.set_confd_users([new_user(1, 'Alice', 'Anderson', '1001')])

        with self.dird_with_config({'wazo_user_cache_ttl': 0}):
            self.wait_strategy.wait(self.dird)
            for _ in range(3):
                assert_that(self.lastnames('alice'), contains_exactly('Anderson'))
            assert_that(self.users_requests(), equal_to(3))

    def test_a_ttl_of_zero_asks_confd_for_each_listing(self):
        """With `wazo_user_cache_ttl: 0` each contacts listing sends its own request."""
        self.set_confd_users([new_user(1, 'Alice', 'Anderson', '1001')])

        with self.dird_with_config({'wazo_user_cache_ttl': 0}):
            self.wait_strategy.wait(self.dird)
            for _ in range(3):
                assert_that(self.contacts()['total'], equal_to(1))
            assert_that(self.users_requests(), equal_to(3))
            by_uuid = self.contacts(uuid=new_user(1, '', '', '')['uuid'])
            assert_that(by_uuid['total'], equal_to(1))
            assert_that(self.users_requests(), equal_to(4))
