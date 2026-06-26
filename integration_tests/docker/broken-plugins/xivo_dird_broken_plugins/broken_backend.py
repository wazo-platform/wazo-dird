# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import threading
import time
from typing import Any

from wazo_dird.plugins.source_result import _SourceResult, make_result_class

first_lock = threading.Lock()


class BrokenPlugin:
    def __init__(self) -> None:
        raise RuntimeError('BROKEN')


class BrokenLookup:
    def load(self, config: dict[str, Any]) -> None:
        return

    def search(
        self, term: str, args: dict[str, Any] | None = None
    ) -> list[_SourceResult]:
        raise RuntimeError('This backend is broken')

    def list(
        self, source_entry_id: list[str], args: dict[str, Any] | None = None
    ) -> list[_SourceResult]:
        raise RuntimeError('This backend is broken')


class ChainedBrokenFirstLookup:
    def load(self, config: dict[str, Any]) -> None:
        first_lock.acquire()
        return

    def first_match(
        self, term: str, args: dict[str, Any] | None = None
    ) -> _SourceResult | None:
        first_lock.release()
        raise RuntimeError('This backend is broken')


class ChainedSecondLookup:
    def load(self, config: dict[str, Any]) -> None:
        self.SourceResult = make_result_class(
            'chained-second-lookup-backend', 'chained-second-lookup'
        )
        return

    def _ensure_first_lookup_has_ended(self) -> None:
        first_lock.acquire()
        first_lock.release()
        time.sleep(0.1)

    def first_match(
        self, term: str, args: dict[str, Any] | None = None
    ) -> _SourceResult | None:
        self._ensure_first_lookup_has_ended()
        return self.SourceResult({'number': '5555555555', 'reverse': 'Second Lookup'})
