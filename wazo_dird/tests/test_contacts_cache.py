# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import threading
import unittest
from unittest.mock import Mock, patch

from hamcrest import (
    assert_that,
    calling,
    contains_exactly,
    equal_to,
    greater_than,
    has_length,
    none,
    raises,
)

from wazo_dird import contacts_cache
from wazo_dird.contacts_cache import ContactsCache, ContactsCacheTimeout


def _cache(ttl=300, max_contacts=100_000, download_timeout=60):
    return ContactsCache(ttl, max_contacts, download_timeout)


class TestContactsCache(unittest.TestCase):
    def test_expired_entries_are_dropped_on_write(self):
        cache = _cache()

        with patch.object(contacts_cache.time, 'monotonic', return_value=1000):
            cache.get_or_fetch('a', Mock(return_value=[]))
        with patch.object(contacts_cache.time, 'monotonic', return_value=1300):
            cache.get_or_fetch('b', Mock(return_value=[]))

        assert_that(cache._entries, has_length(1))

    def test_expired_entries_are_fetched_again(self):
        cache = _cache()
        fetch = Mock(return_value=[])

        with patch.object(contacts_cache.time, 'monotonic', return_value=1000):
            cache.get_or_fetch('a', fetch)
        with patch.object(contacts_cache.time, 'monotonic', return_value=1299):
            cache.get_or_fetch('a', fetch)
        assert_that(fetch.call_count, equal_to(1))
        with patch.object(contacts_cache.time, 'monotonic', return_value=1300):
            cache.get_or_fetch('a', fetch)

        assert_that(fetch.call_count, equal_to(2))

    def test_oldest_entry_is_evicted_when_full(self):
        cache = _cache(max_contacts=2)

        for key in ('a', 'b', 'c'):
            cache.get_or_fetch(key, Mock(return_value=[{'id': key}]))

        fetch = Mock(return_value=[])
        cache.get_or_fetch('b', fetch)
        cache.get_or_fetch('c', fetch)
        fetch.assert_not_called()
        cache.get_or_fetch('a', fetch)
        fetch.assert_called_once_with()

    def test_entries_are_evicted_until_the_contacts_fit(self):
        cache = _cache(max_contacts=3)

        for key in ('a', 'b', 'c'):
            cache.get_or_fetch(key, Mock(return_value=[{'id': key}]))
        cache.get_or_fetch('d', Mock(return_value=[{'id': 'd1'}, {'id': 'd2'}]))

        assert_that(list(cache._entries), contains_exactly('c', 'd'))
        assert_that(cache._contact_count, equal_to(3))

    def test_contacts_above_the_limit_are_not_cached(self):
        cache = _cache(max_contacts=2)
        cache.get_or_fetch('a', Mock(return_value=[{'id': 'a'}]))

        contacts = [{'id': 'b1'}, {'id': 'b2'}, {'id': 'b3'}]
        fetch = Mock(return_value=contacts)
        with self.assertLogs(contacts_cache.logger, 'WARNING'):
            assert_that(cache.get_or_fetch('b', fetch), equal_to(contacts))
        assert_that(cache.get_or_fetch('b', fetch), equal_to(contacts))

        assert_that(fetch.call_count, equal_to(2))
        assert_that(list(cache._entries), contains_exactly('a'))
        assert_that(cache._contact_count, equal_to(1))

    def test_interrupted_fetch_does_not_block_later_fetches(self):
        cache = _cache()

        assert_that(
            calling(cache.get_or_fetch).with_args(
                'a', Mock(side_effect=KeyboardInterrupt)
            ),
            raises(KeyboardInterrupt),
        )

        fetch = Mock(return_value=[{'id': 'a'}])
        assert_that(cache.get_or_fetch('a', fetch), contains_exactly({'id': 'a'}))
        fetch.assert_called_once_with()

    def test_a_failure_is_not_stored(self):
        cache = _cache()

        assert_that(
            calling(cache.get_or_fetch).with_args('a', Mock(side_effect=OSError)),
            raises(OSError),
        )

        fetch = Mock(return_value=[{'id': 'a'}])
        cache.get_or_fetch('a', fetch)
        fetch.assert_called_once_with()

    def test_waiters_give_up_at_the_download_timeout(self):
        cache = _cache(download_timeout=0.01)
        fetching = threading.Event()
        release = threading.Event()

        def slow_fetch():
            fetching.set()
            release.wait(5)
            return []

        fetcher = threading.Thread(target=cache.get_or_fetch, args=('a', slow_fetch))
        try:
            fetcher.start()
            fetching.wait(5)
            assert_that(
                calling(cache.get_or_fetch).with_args('a', Mock()),
                raises(ContactsCacheTimeout),
            )
            assert_that(fetcher.is_alive(), equal_to(True))
        finally:
            release.set()
            fetcher.join(5)


class TestContactsCacheVersions(unittest.TestCase):
    def test_a_stored_list_keeps_its_version_until_it_is_fetched_again(self):
        cache = _cache()

        first, _ = cache.get_or_fetch_versioned('a', Mock(return_value=[1]))
        again, _ = cache.get_or_fetch_versioned('a', Mock(return_value=[2]))
        cache.evict('a')
        refetched, contacts = cache.get_or_fetch_versioned('a', Mock(return_value=[3]))

        assert_that(first, equal_to(again))
        assert_that(refetched, greater_than(first))
        assert_that(contacts, equal_to([3]))

    def test_versions_are_unique_across_keys(self):
        cache = _cache()

        a, _ = cache.get_or_fetch_versioned('a', Mock(return_value=[1]))
        b, _ = cache.get_or_fetch_versioned('b', Mock(return_value=[1]))

        assert_that(a, equal_to(1))
        assert_that(b, equal_to(2))

    def test_a_list_above_the_bound_has_no_version(self):
        cache = _cache(max_contacts=1)

        version, contacts = cache.get_or_fetch_versioned('a', Mock(return_value=[1, 2]))

        assert_that(version, none())
        assert_that(contacts, equal_to([1, 2]))


class TestContactsCacheEvict(unittest.TestCase):
    def test_evict_forgets_the_stored_list(self):
        cache = _cache()
        cache.get_or_fetch('a', Mock(return_value=[1]))

        cache.evict('a')

        fetch = Mock(return_value=[2])
        assert_that(cache.get_or_fetch('a', fetch), equal_to([2]))
        fetch.assert_called_once_with()
        assert_that(cache._contact_count, equal_to(1))

    def test_evict_of_a_key_never_stored_does_nothing(self):
        cache = _cache()

        cache.evict('never-listed')

        assert_that(cache._entries, equal_to({}))

    def test_evict_during_a_fetch_keeps_its_result_out_of_the_cache(self):
        cache = _cache()
        fetching = threading.Event()
        release = threading.Event()
        results = []

        def slow_fetch():
            fetching.set()
            release.wait(5)
            return ['stale']

        fetcher = threading.Thread(
            target=lambda: results.append(cache.get_or_fetch_versioned('a', slow_fetch))
        )
        fetcher.start()
        fetching.wait(5)
        cache.evict('a')
        release.set()
        fetcher.join(5)

        assert_that(results, contains_exactly((None, ['stale'])))
        fetch = Mock(return_value=['fresh'])
        assert_that(cache.get_or_fetch('a', fetch), equal_to(['fresh']))
        fetch.assert_called_once_with()

    def test_a_caller_after_evict_fetches_again_while_the_old_fetch_runs(self):
        cache = _cache()
        fetching = threading.Event()
        release = threading.Event()
        old = []

        def slow_fetch():
            fetching.set()
            release.wait(5)
            return ['stale']

        fetcher = threading.Thread(
            target=lambda: old.append(cache.get_or_fetch_versioned('a', slow_fetch))
        )
        fetcher.start()
        try:
            fetching.wait(5)
            cache.evict('a')
            fetch = Mock(return_value=['fresh'])
            version, contacts = cache.get_or_fetch_versioned('a', fetch)
        finally:
            release.set()
            fetcher.join(5)

        fetch.assert_called_once_with()
        assert_that(contacts, equal_to(['fresh']))
        assert_that(old, contains_exactly((None, ['stale'])))
        # the old fetch ending neither stores nor detaches the fresh one
        assert_that(
            cache.get_or_fetch_versioned('a', Mock()), equal_to((version, ['fresh']))
        )


class TestContactsCacheExpiryAndLogs(unittest.TestCase):
    def test_drop_expired_evicts_only_the_expired_lists_and_reports_them(self):
        evicted: list[str] = []
        cache: ContactsCache[int] = ContactsCache(30, 100, 60, on_evict=evicted.append)
        with patch.object(contacts_cache.time, 'monotonic', return_value=1000):
            cache.get_or_fetch('old', Mock(return_value=[1]))
        with patch.object(contacts_cache.time, 'monotonic', return_value=1020):
            cache.get_or_fetch('new', Mock(return_value=[2]))

        with patch.object(contacts_cache.time, 'monotonic', return_value=1030):
            cache.drop_expired()

        assert_that(evicted, contains_exactly('old'))
        fetch = Mock(return_value=[])
        with patch.object(contacts_cache.time, 'monotonic', return_value=1031):
            cache.get_or_fetch('new', fetch)
            cache.get_or_fetch('old', fetch)
        assert_that(fetch.call_count, equal_to(1))

    def test_every_eviction_is_reported(self):
        evicted: list[str] = []
        cache: ContactsCache[str] = ContactsCache(30, 2, 60, on_evict=evicted.append)
        for key in ('a', 'b', 'c'):
            cache.get_or_fetch(key, Mock(return_value=[key]))
        cache.evict('b')

        assert_that(evicted, contains_exactly('a', 'b'))

    def test_a_timeout_raised_by_the_fetch_is_not_a_wait_timeout(self):
        cache = _cache()
        error = TimeoutError('socket timed out')

        assert_that(
            calling(cache.get_or_fetch).with_args('a', Mock(side_effect=error)),
            raises(TimeoutError, 'socket timed out'),
        )

    def test_logs_name_a_key_by_its_prefix_only(self):
        cache = _cache(max_contacts=1)
        key = 'k' * 12 + 'SECRET-TAIL'

        with self.assertLogs(contacts_cache.logger, 'DEBUG') as logs:
            cache.get_or_fetch(key, Mock(return_value=[1, 2]))

        assert_that(any('k' * 12 in m for m in logs.output), equal_to(True))
        assert_that(any('SECRET-TAIL' in m for m in logs.output), equal_to(False))
