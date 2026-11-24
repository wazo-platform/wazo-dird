# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
import logging
import threading
import time
from bisect import bisect_left, bisect_right
from collections.abc import Iterable, Mapping
from typing import NamedTuple

from wazo_dird.plugins.source_result import _SourceResult as SourceResult

logger = logging.getLogger(__name__)

SortKey = tuple[str, str]
# A member source of a tenant: its uuid, the version and the list cached
Member = tuple[int, list[SourceResult]]


def sort_key(result: SourceResult) -> SortKey:
    """The listing order: source name, then contact id, else the fields"""
    entry_id = result.source_entry_id()
    if entry_id is None:
        entry_id = json.dumps(result.fields, sort_keys=True, default=str)
    return result.source, str(entry_id)


class SortedContacts(NamedTuple):
    keys: list[SortKey]
    results: list[SourceResult]


def build_sorted(lists: Iterable[list[SourceResult]]) -> SortedContacts:
    """The shared sort, paid once per change of a tenant's member sources"""
    return _sort(lists)


def _sort(lists: Iterable[list[SourceResult]]) -> SortedContacts:
    keyed = sorted(
        ((sort_key(result), result) for results in lists for result in results),
        key=lambda pair: pair[0],
    )
    return SortedContacts([key for key, _ in keyed], [result for _, result in keyed])


def page_by_rank(
    shared: SortedContacts, fresh: list[SourceResult], offset: int, limit: int
) -> list[SourceResult]:
    """The [offset, offset + limit) slice of shared and fresh merged and
    sorted, without merging them: a fresh contact equal to a shared one comes
    after it, as a stable sort of shared then fresh would place it."""
    fresh_sorted = _sort([fresh])
    # The rank of each fresh contact in the merge: the shared ones before it,
    # plus the fresh ones before it
    ranks = [
        bisect_right(shared.keys, key) + index
        for index, key in enumerate(fresh_sorted.keys)
    ]
    fresh_index = bisect_left(ranks, offset)
    shared_index = offset - fresh_index
    page: list[SourceResult] = []
    while len(page) < limit:
        rank = shared_index + fresh_index
        if fresh_index < len(ranks) and ranks[fresh_index] == rank:
            page.append(fresh_sorted.results[fresh_index])
            fresh_index += 1
        elif shared_index < len(shared.results):
            page.append(shared.results[shared_index])
            shared_index += 1
        else:
            break
    return page


class _Entry(NamedTuple):
    expires_at: float
    versions: tuple[int, ...]
    contacts: SortedContacts


class TenantSortedIndex:
    """Each tenant's merged and sorted list of its cacheable sources, kept
    while none of them changes, so that reading page after page sorts once.

    An entry is keyed by the tenant and its member sources, and reused only
    while every member's cached list is the version it was built from.
    """

    def __init__(self, ttl: float) -> None:
        self.ttl = ttl
        self.builds = 0
        self._lock = threading.Lock()
        self._entries: dict[tuple[str, tuple[str, ...]], _Entry] = {}
        self._build_locks: dict[tuple[str, tuple[str, ...]], threading.Lock] = {}

    def get(self, tenant_uuid: str, members: Mapping[str, Member]) -> SortedContacts:
        uuids = tuple(sorted(members))
        key = (tenant_uuid, uuids)
        versions = tuple(members[uuid][0] for uuid in uuids)
        with self._lock:
            build_lock = self._build_locks.setdefault(key, threading.Lock())
        # One build per tenant at a time: the others wait and reuse it
        with build_lock:
            with self._lock:
                entry = self._valid_entry(key, versions)
            if entry is not None:
                return entry.contacts
            contacts = self.build(members[uuid][1] for uuid in uuids)
            with self._lock:
                self._drop_expired()
                self._entries[key] = _Entry(
                    time.monotonic() + self.ttl, versions, contacts
                )
            logger.debug(
                'sorted %d contacts of %d sources for tenant %s',
                len(contacts.results),
                len(uuids),
                tenant_uuid,
            )
            return contacts

    def build(self, lists: Iterable[list[SourceResult]]) -> SortedContacts:
        self.builds += 1
        return build_sorted(lists)

    def forget_source(self, source_uuid: str) -> None:
        with self._lock:
            for key in [key for key in self._entries if source_uuid in key[1]]:
                del self._entries[key]

    def _valid_entry(
        self, key: tuple[str, tuple[str, ...]], versions: tuple[int, ...]
    ) -> _Entry | None:
        # Called with self._lock held
        entry = self._entries.get(key)
        if entry is None or entry.versions != versions:
            return None
        if entry.expires_at <= time.monotonic():
            del self._entries[key]
            return None
        return entry

    def _drop_expired(self) -> None:
        # Called with self._lock held
        now = time.monotonic()
        for key in [key for key, e in self._entries.items() if e.expires_at <= now]:
            del self._entries[key]
