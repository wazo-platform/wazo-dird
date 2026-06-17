# Copyright 2020-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from sys import maxunicode
from typing import Any

from unidecode import unidecode

MAX_CHAR: str = chr(maxunicode)
ALMOST_LAST_STRING: str = MAX_CHAR * 16


def sort_contacts(
    contacts: list[dict[str, Any]],
    order: str | None = None,
    direction: str | None = None,
    order_insensitive: bool = False,
    **_: Any,  # TODO: remove this parameter
) -> list[dict[str, Any]]:
    if not order:
        return contacts

    reverse = direction == "desc"

    def get_value(contact: dict[str, Any]) -> str:
        value = contact.get(order)
        if not value:
            return ALMOST_LAST_STRING

        if isinstance(value, str):
            if order_insensitive:
                value = value.casefold()
            decoded: str = unidecode(value)
            return decoded

        return str(value)

    return sorted(contacts, key=get_value, reverse=reverse)
