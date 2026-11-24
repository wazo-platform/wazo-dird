# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import random
import unittest
from unittest.mock import Mock, patch

from hamcrest import (
    assert_that,
    contains_exactly,
    empty,
    equal_to,
    greater_than_or_equal_to,
    has_length,
)

from wazo_dird import contacts_cache
from wazo_dird.exception import SourceListError
from wazo_dird.plugins.source_result import make_result_class

from .. import sorted_index
from ..plugin import _LookupService
from ..sorted_index import build_sorted, page_by_rank, sort_key
from .fakes import FakeSource, FakeSourceManager, config, contacts, profile

TENANT = 'tenant-uuid'


def _results(source, ids, unique_column='id'):
    SourceResult = make_result_class('csv', source, unique_column)
    return [SourceResult({'id': i, 'name': f'{source}-{i}'}) for i in ids]


def _reference(*lists):
    merged = [item for items in lists for item in items]
    return sorted(merged, key=sort_key)


class TestSortKey(unittest.TestCase):
    def test_by_source_name_then_contact_id(self):
        items = _results('b', ['2', '1']) + _results('a', ['9'])

        assert_that(
            [(r.source, r.source_entry_id()) for r in sorted(items, key=sort_key)],
            contains_exactly(('a', '9'), ('b', '1'), ('b', '2')),
        )

    def test_without_an_id_the_fields_serialized_with_sorted_keys(self):
        SourceResult = make_result_class('csv', 'a', None)
        result = SourceResult({'z': 1, 'b': 'x'})

        assert_that(
            sort_key(result),
            equal_to(('a', json.dumps({'b': 'x', 'z': 1}, sort_keys=True))),
        )


class TestPageByRank(unittest.TestCase):
    def test_every_page_equals_the_same_slice_of_a_full_sort(self):
        rng = random.Random(290)
        for case in range(200):
            shared = _results('s', [f'{rng.randrange(10_000):05d}' for _ in range(rng.randrange(501))])
            shared += _results('u', [f'{rng.randrange(10_000):05d}' for _ in range(rng.randrange(50))])
            fresh = _results('s', [f'{rng.randrange(10_000):05d}' for _ in range(rng.randrange(51))])
            fresh += _results('p', [f'{rng.randrange(10_000):05d}' for _ in range(rng.randrange(5))])
            rng.shuffle(fresh)
            limit = rng.randint(1, 100)
            offset = rng.randint(0, 600)

            page = page_by_rank(build_sorted([shared]), fresh, offset, limit)

            expected = _reference(shared, fresh)[offset : offset + limit]
            assert_that(
                [sort_key(r) for r in page],
                equal_to([sort_key(r) for r in expected]),
                f'case {case}: offset {offset} limit {limit}',
            )

    def test_a_fresh_contact_equal_to_a_shared_one_comes_after_it(self):
        shared = _results('s', ['1'])
        fresh = _results('s', ['1'])

        page = page_by_rank(build_sorted([shared]), fresh, 0, 2)

        assert_that(page[0], equal_to(shared[0]))
        assert_that(page[1] is fresh[0], equal_to(True))

    def test_a_page_past_the_end_is_empty(self):
        page = page_by_rank(build_sorted([_results('s', ['1'])]), [], 5, 10)

        assert_that(page, empty())


class _ListingTest(unittest.TestCase):
    def _service(self, sources, **conf):
        self.manager = FakeSourceManager(sources)
        self.service = _LookupService(config(**conf), self.manager, Mock())
        self.profiles = [profile('p', lookup=list(sources))]

    def _read_every_page(self, limit=100):
        pages, offset = [], 0
        while True:
            items, total, _ = self.service.list_page(
                self.profiles, TENANT, None, 'token', limit, offset
            )
            if not items:
                return pages, total
            pages.append(items)
            offset += limit


class TestTenantSortedList(_ListingTest):
    def test_reading_every_page_builds_the_sorted_list_once(self):
        self._service(
            {
                'u-a': FakeSource('a', contacts('a', 400)),
                'u-b': FakeSource('b', contacts('b', 300)),
                'u-c': FakeSource('c', contacts('c', 300)),
            }
        )

        with patch.object(sorted_index, 'build_sorted', wraps=build_sorted) as build:
            pages, total = self._read_every_page()

        assert_that(build.call_count, equal_to(1))
        assert_that(self.service._sorted_index.builds, equal_to(1))
        assert_that(pages, has_length(10))
        assert_that(total, equal_to(1000))

    def test_fresh_contacts_are_placed_between_shared_ones_on_every_page(self):
        shared = contacts('s', 250)
        fresh = [{'id': f's{i:05d}x', 'name': f'fresh {i}'} for i in range(0, 250, 7)]
        self._service(
            {
                'u-s': FakeSource('src', shared),
                'u-f': FakeSource('src', fresh, cacheable=False),
            }
        )

        pages, total = self._read_every_page(limit=33)

        listed = [sort_key(r) for page in pages for r in page]
        reference = _reference(
            FakeSource('src', shared).list_all(),
            FakeSource('src', fresh, cacheable=False).list_all(),
        )
        assert_that(listed, equal_to([sort_key(r) for r in reference]))
        assert_that(total, equal_to(250 + len(fresh)))

    def test_a_refetched_or_evicted_source_rebuilds_the_list(self):
        self._service(
            {
                'u-a': FakeSource('a', contacts('a', 3)),
                'u-b': FakeSource('b', contacts('b', 3)),
            }
        )
        clock = [1000.0]
        with patch.object(contacts_cache.time, 'monotonic', side_effect=lambda: clock[0]), patch.object(
            sorted_index.time, 'monotonic', side_effect=lambda: clock[0]
        ):
            self._read_every_page()
            self._read_every_page()
            assert_that(self.service._sorted_index.builds, equal_to(1))

            clock[0] += 30
            self._read_every_page()
            assert_that(self.service._sorted_index.builds, equal_to(2))

            self.manager.invalidate('u-a')
            self._read_every_page()
            assert_that(self.service._sorted_index.builds, equal_to(3))

    def test_a_failed_member_answers_but_stores_nothing(self):
        failing = FakeSource('b', contacts('b', 3))
        self._service({'u-a': FakeSource('a', contacts('a', 3)), 'u-b': failing})
        failing.error = SourceListError('b')

        items, total, missing = self.service.list_page(
            self.profiles, TENANT, None, 'token', 100, 0
        )

        assert_that((total, missing), equal_to((3, ['b'])))
        assert_that(self.service._sorted_index._entries, empty())


class TestBound(_ListingTest):
    def test_lists_past_the_bound_evict_each_other_and_pages_stay_right(self):
        a, b = FakeSource('a', contacts('a', 60)), FakeSource('b', contacts('b', 60))
        self._service({'u-a': a, 'u-b': b}, max_contacts=100)

        with self.assertLogs(contacts_cache.logger, 'INFO') as logs:
            pages, total = self._read_every_page(limit=7)

        listed = [sort_key(r) for page in pages for r in page]
        assert_that(listed, equal_to([sort_key(r) for r in _reference(a.list_all(), b.list_all())]))
        assert_that(total, equal_to(120))
        # both lists never fit: every listing, the empty last page's included,
        # stores one and evicts the other, and a race can make it two
        evictions = [m for m in logs.output if 'Evicting oldest' in m]
        assert_that(len(evictions), greater_than_or_equal_to(len(pages) + 1))

    def test_a_source_above_the_bound_is_listed_on_every_page_never_stored(self):
        big = FakeSource('big', contacts('g', 20))
        small = FakeSource('small', contacts('m', 5))
        self._service({'u-big': big, 'u-small': small}, max_contacts=10)

        with self.assertLogs(contacts_cache.logger, 'WARNING'):
            pages, total = self._read_every_page(limit=10)

        listed = [sort_key(r) for page in pages for r in page]
        assert_that(listed, equal_to([sort_key(r) for r in _reference(big.list_all(), small.list_all())]))
        # one call per listing, the empty last page's included, plus _reference's
        assert_that(len(big.list_calls), equal_to(len(pages) + 2))
        assert_that(len(small.list_calls), equal_to(2))
        assert_that(self.service._sorted_index._entries, empty())

    def test_a_failed_user_scoped_source_does_not_stop_the_shared_list(self):
        personal = FakeSource('personal', contacts('p', 1), cacheable=False)
        personal.error = SourceListError('personal')
        self._service({'u-a': FakeSource('a', contacts('a', 3)), 'u-p': personal})

        _, total, missing = self.service.list_page(
            self.profiles, TENANT, None, 'token', 100, 0
        )

        assert_that((total, missing), equal_to((3, ['personal'])))
        assert_that(self.service._sorted_index._entries, has_length(1))
