# Copyright 2020-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import unicodedata
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
        order_insensitive: bool = False,
        **_: Any,  # TODO: remove this parameter
    ) -> list[dict]:
        if not order:
            return contacts

        reverse = direction == "desc"

        def get_value(contact: dict) -> str:
            value = contact.get(order)
            if not value:
                return ALMOST_LAST_STRING

            if isinstance(value, str):
                if order_insensitive:
                    value = value.casefold()
                value = unicodedata.normalize('NFKD', value)

            return value

        return sorted(contacts, key=get_value, reverse=reverse)
