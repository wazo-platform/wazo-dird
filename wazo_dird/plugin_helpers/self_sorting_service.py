# Copyright 2020-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from sys import maxunicode
from typing import Any

MAX_CHAR: str = chr(maxunicode)
ALMOST_LAST_STRING: str = MAX_CHAR * 16


class SelfSortingServiceMixin:
    @staticmethod
    def sort(
        contacts: list[dict],
        order: str | None = None,
        direction: str | None = None,
        **_: Any,  # TODO: remove this parameter
    ) -> list[dict]:
        if not order:
            return contacts

        reverse = direction == "desc"

        def get_value(contact: dict) -> str:
            value = contact.get(order)
            return value or ALMOST_LAST_STRING

        return sorted(contacts, key=get_value, reverse=reverse)
