# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import concurrent.futures
import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass, field
from typing import Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')

# A list not stored in the cache has no version
Versioned = tuple['int | None', list[T]]


class ContactsCacheTimeout(Exception):
    def __init__(self, key: str, timeout: float) -> None:
        super().__init__(
            f'Gave up waiting {timeout} seconds for the contacts of key {key}'
        )


@dataclass
class _Fetch(Generic[T]):
    future: Future[Versioned[T]] = field(default_factory=lambda: Future())
    # Set by evict: the result goes to its waiters but is not stored
    evicted: bool = False


class ContactsCache(Generic[T]):
    """Thread-safe TTL cache of contact lists, by key.

    Concurrent misses for a key share one fetch, including its failure, and a
    failure is never stored. The number of contacts held across every key is
    bounded: the oldest entries are evicted to make room, and a list larger
    than the bound is never stored. The returned lists are shared: callers
    must not mutate them.
    """

    def __init__(self, ttl: float, max_contacts: int, download_timeout: float) -> None:
        self.ttl = ttl
        self.max_contacts = max_contacts
        self.download_timeout = download_timeout
        self._lock = threading.Lock()
        self._entries: dict[str, tuple[float, int, list[T]]] = {}
        self._contact_count = 0
        self._fetches: dict[str, _Fetch[T]] = {}
        # One counter for every key, so a version names one stored list
        self._last_version = 0

    def get_or_fetch(self, key: str, fetch: Callable[[], list[T]]) -> list[T]:
        return self.get_or_fetch_versioned(key, fetch)[1]

    def get_or_fetch_versioned(
        self, key: str, fetch: Callable[[], list[T]]
    ) -> Versioned[T]:
        """The list of key, with the version it was stored under, or None if
        it was not stored. Raises what fetch raised, or ContactsCacheTimeout
        when a fetch in progress outlasts download_timeout."""
        with self._lock:
            entry = self._get(key)
            if entry is not None:
                version, contacts = entry
                logger.debug(
                    'contacts cache hit for key %s: %d contacts', key, len(contacts)
                )
                return version, contacts
            in_progress, is_fetcher = self._join_or_start(key)

        if is_fetcher:
            self._run(key, in_progress, fetch)
        try:
            return in_progress.future.result(self.download_timeout)
        except concurrent.futures.TimeoutError:
            logger.warning(
                'Gave up waiting %s seconds for the contacts of key %s',
                self.download_timeout,
                key,
            )
            raise ContactsCacheTimeout(key, self.download_timeout)

    def evict(self, key: str) -> None:
        """Forget the list of key, and keep a fetch in progress from storing it"""
        with self._lock:
            if key in self._entries:
                self._evict(key)
            in_progress = self._fetches.get(key)
            if in_progress is not None:
                in_progress.evicted = True
            logger.debug('contacts cache evicted key %s', key)

    def _join_or_start(self, key: str) -> tuple[_Fetch[T], bool]:
        # Called with self._lock held
        in_progress = self._fetches.get(key)
        if in_progress is not None:
            logger.debug(
                'contacts cache miss for key %s: waiting for the fetch in progress',
                key,
            )
            return in_progress, False
        logger.debug('contacts cache miss for key %s: fetching', key)
        in_progress = self._fetches[key] = _Fetch()
        return in_progress, True

    def _run(self, key: str, fetch_: _Fetch[T], fetch: Callable[[], list[T]]) -> None:
        try:
            contacts = fetch()
            with self._lock:
                version = None if fetch_.evicted else self._set(key, contacts)
        except Exception as e:
            fetch_.future.set_exception(e)
        else:
            fetch_.future.set_result((version, contacts))
        finally:
            # Also on BaseException: a stale entry would block every later fetch
            with self._lock:
                del self._fetches[key]

    def _get(self, key: str) -> tuple[int, list[T]] | None:
        # Called with self._lock held
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, version, contacts = entry
        if expires_at <= time.monotonic():
            logger.debug('contacts cache entry expired: key %s', key)
            self._evict(key)
            return None
        return version, contacts

    def _set(self, key: str, contacts: list[T]) -> int | None:
        # Called with self._lock held
        now = time.monotonic()
        if key in self._entries:
            self._evict(key)
        if len(contacts) > self.max_contacts:
            # Storing it would evict every other key and exceed the bound
            logger.warning(
                'Not caching %d contacts for key %s: above the limit of %d',
                len(contacts),
                key,
                self.max_contacts,
            )
            return None
        # Every entry has the same TTL and is inserted last, so the oldest
        # entries are the first to expire
        while self._entries:
            oldest_key, (expires_at, _, _) = next(iter(self._entries.items()))
            if expires_at <= now:
                logger.debug(
                    'Evicting expired contacts cache entry: key %s', oldest_key
                )
            elif self._contact_count + len(contacts) > self.max_contacts:
                logger.info(
                    'Evicting oldest contacts cache entry: key %s, '
                    'the cache is full (%d contacts)',
                    oldest_key,
                    self._contact_count,
                )
            else:
                break
            self._evict(oldest_key)
        self._last_version += 1
        self._entries[key] = (now + self.ttl, self._last_version, contacts)
        self._contact_count += len(contacts)
        return self._last_version

    def _evict(self, key: str) -> None:
        # Called with self._lock held
        _, _, contacts = self._entries.pop(key)
        self._contact_count -= len(contacts)
