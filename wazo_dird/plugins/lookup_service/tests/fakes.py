# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from wazo_dird import BaseSourcePlugin, make_result_class
from wazo_dird.plugins.base_plugins import LookupArgs
from wazo_dird.plugins.source_result import _SourceResult as SourceResult


class FakeSource(BaseSourcePlugin):
    """A source whose list_all is counted; search and reverse are refused."""

    def __init__(
        self,
        name: str,
        contacts: list[dict[str, Any]],
        cacheable: bool = True,
        backend: str = 'csv',
        unique_column: str | None = 'id',
        is_personal: bool = False,
    ) -> None:
        self.name = name
        self.backend = backend
        self.list_cacheable = cacheable
        self.contacts = contacts
        self.error: Exception | None = None
        self.gate: threading.Event | None = None
        self.on_list: Callable[[], None] | None = None
        self.list_calls: list[LookupArgs | None] = []
        self._SourceResult = make_result_class(
            backend, name, unique_column, is_personal=is_personal
        )

    def load(self, args: Any) -> None:
        pass

    def search(self, term: str, args: Any = None) -> list[SourceResult]:
        raise AssertionError(f'{self.name}: search must not be called')

    def first_match(self, exten: str, args: Any = None) -> SourceResult | None:
        raise AssertionError(f'{self.name}: first_match must not be called')

    def list_all(self, args: LookupArgs | None = None) -> list[SourceResult]:
        self.list_calls.append(args)
        if self.on_list:
            self.on_list()
        if self.gate is not None:
            self.gate.wait(10)
        if self.error is not None:
            raise self.error
        return [self._SourceResult(c) for c in self.contacts]


class FakeSourceManager:
    def __init__(self, sources: dict[str, BaseSourcePlugin]) -> None:
        self.sources = sources
        self._subscribers: list[Callable[[str], None]] = []

    def get(self, uuid: str) -> BaseSourcePlugin | None:
        return self.sources.get(uuid)

    def subscribe_invalidate(self, callback: Callable[[str], None]) -> None:
        self._subscribers.append(callback)

    def invalidate(self, uuid: str) -> None:
        for callback in self._subscribers:
            callback(uuid)


def profile(name: str, **services: list[str]) -> dict[str, Any]:
    return {
        'name': name,
        'services': {
            service: {'sources': [{'uuid': uuid, 'name': uuid} for uuid in uuids]}
            for service, uuids in services.items()
        },
    }


def config(timeout: float = 10, cache_ttl: int = 30, max_contacts: int = 100_000):
    return {
        'rest_api': {'max_threads': 10},
        'contacts_list': {
            'timeout': timeout,
            'cache_ttl': cache_ttl,
            'cache_max_contacts': max_contacts,
        },
    }


def contacts(prefix: str, count: int) -> list[dict[str, Any]]:
    return [{'id': f'{prefix}{i:05d}', 'name': f'{prefix} {i}'} for i in range(count)]
