# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import time

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


class TestWazoUserSnapshotPaging(BaseSnapshotTest):
    def test_the_load_pages_through_all_the_users(self):
        """The load asks 1,000 users at a time, up to `total`, with no user twice."""
        users = [
            new_user(i, 'Filler', f'N{i:04d}', str(2000 + i)) for i in range(1, 2500)
        ]
        users.append(new_user(2500, 'Zelda', 'Thirdpage', '9999'))
        self.set_confd_users(users)
        self.expire_snapshot()

        assert_that(self.lastnames('thirdpage'), contains_exactly('Thirdpage'))
        assert_that(
            self.confd_stats()['pages'],
            contains_exactly([1000, 0], [1000, 1000], [1000, 2000]),
        )

        results = self.lookup('filler', 'default')['results']
        entry_ids = {result['relations']['source_entry_id'] for result in results}
        assert_that(results, has_length(2499))
        assert_that(entry_ids, has_length(2499))
        assert_that(self.users_requests(), equal_to(3))

    def test_a_confd_that_ignores_the_offset_does_not_hang_the_load(self):
        """The load stops when a page adds no user, whatever `total` says."""
        users = [new_user(i, 'Filler', f'N{i}', str(3000 + i)) for i in range(1, 6)]
        self.set_confd_users(users, ignore_offset=True, total=10000)
        self.expire_snapshot()

        started = time.monotonic()
        assert_that(self.lastnames('filler'), has_length(5))
        assert_that(time.monotonic() - started, less_than(5))
        loaded = self.users_requests()
        assert_that(loaded, less_than_or_equal_to(3))

        assert_that(self.lastnames('filler'), has_length(5))
        assert_that(self.users_requests(), equal_to(loaded))


class TestWazoUserSnapshotDisabled(BaseSnapshotTest):
    def test_a_ttl_of_zero_asks_confd_for_each_lookup(self):
        """With `wazo_user_cache_ttl: 0` each lookup sends its own request."""
        self.set_confd_users([new_user(1, 'Alice', 'Anderson', '1001')])

        with self.dird_with_config({'wazo_user_cache_ttl': 0}):
            self.wait_strategy.wait(self.dird)
            for _ in range(3):
                assert_that(self.lastnames('alice'), contains_exactly('Anderson'))
            assert_that(self.users_requests(), equal_to(3))
