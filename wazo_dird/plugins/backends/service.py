# Copyright 2018-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any

from wazo_dird.config import Config
from wazo_dird.plugin_helpers.sorting import sort_contacts


class BackendService:
    _backend_entry_points = 'wazo_dird.backends'

    def __init__(self, config: Config) -> None:
        configured_backends = set()
        for backend_name, enabled in config['enabled_plugins']['backends'].items():
            if not enabled:
                continue
            configured_backends.add(backend_name)

        installed_backends = {
            module.name for module in entry_points(group=self._backend_entry_points)
        }

        self._backends: list[dict[str, str]] = [
            {'name': backend} for backend in configured_backends & installed_backends
        ]

    def list_(self, **kwargs: Any) -> list[dict[str, Any]]:
        matches = self._filter_matches(self._backends, **kwargs)
        filtered = sort_contacts(matches, **kwargs)
        paginated = self._paginate(filtered, **kwargs)
        return paginated

    def count(self, **kwargs: Any) -> int:
        return len(self._filter_matches(self._backends, **kwargs))

    @staticmethod
    def _filter_matches(
        backends: list[dict[str, str]],
        search: str | None = None,
        **kwargs: Any,
    ) -> list[dict[str, str]]:
        searchable_fields = ['name']
        matchers: list[Callable[[dict[str, str]], bool]] = []

        if search is not None:
            for field in searchable_fields:
                matchers.append(lambda backend: search in backend[field])

        for field in searchable_fields:
            if field not in kwargs:
                continue
            matchers.append(lambda backend: kwargs[field] == backend[field])

        if not matchers:
            return backends

        matches = []

        for backend in backends:
            for matcher in matchers:
                if matcher(backend):
                    matches.append(backend)
                    continue

        return matches

    @staticmethod
    def _paginate(
        backends: list[dict[str, Any]],
        limit: int | None = None,
        offset: int = 0,
        **ignored: Any,
    ) -> list[dict[str, Any]]:
        offset = 0 or offset

        if limit is not None:
            return backends[offset : limit + offset]

        return backends[offset:]
