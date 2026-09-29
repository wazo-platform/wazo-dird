# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import inspect
import unittest
from importlib.metadata import entry_points
from typing import Any

from hamcrest import assert_that, equal_to, has_entries

from wazo_dird.plugins.base_plugins import BaseSourcePlugin, SourcePluginDependencies
from wazo_dird.plugins.source_result import _SourceResult as SourceResult


class _MinimalSource(BaseSourcePlugin):
    """A backend that implements only what the contract makes mandatory."""

    def load(self, args: SourcePluginDependencies) -> None:
        pass

    def search(
        self, term: str, args: dict[str, Any] | None = None
    ) -> list[SourceResult]:
        return []

    def first_match(
        self, exten: str, args: dict[str, Any] | None = None
    ) -> SourceResult | None:
        return None


class TestCanonicalUniqueId(unittest.TestCase):
    def setUp(self):
        self._source = _MinimalSource()

    def test_a_backend_stores_any_id_unchanged_by_default(self):
        # most backends have ids of no recognisable shape, so the contract
        # must not force them to translate or to check
        for unique_id in ['226', 'abcd', '', 'a/b c', '7ca42f43-8bd9-4a26-acb8-cb']:
            assert_that(
                self._source.canonical_unique_id(unique_id), equal_to(unique_id)
            )

    def test_a_backend_translates_nothing_by_default(self):
        for unique_id in ['226', 'abcd', '', 'a/b c', '7ca42f43-8bd9-4a26-acb8-cb']:
            assert_that(
                self._source.translate_unique_id(unique_id), equal_to(unique_id)
            )


class TestSearchSignature(unittest.TestCase):
    def test_every_backend_receives_lookup_args_passed_positionally(self):
        # the lookup service calls source.search(term, args)
        lookup_args = {'token': 'a-token', 'user_uuid': 'a-uuid'}
        for entry_point in entry_points(group='wazo_dird.backends'):
            backend = entry_point.load()
            with self.subTest(backend=entry_point.name):
                bound = inspect.signature(backend.search).bind(
                    backend, 'a-term', lookup_args
                )
                assert_that(bound.arguments, has_entries(args=lookup_args))
