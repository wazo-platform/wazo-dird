# Copyright 2024-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Mapping
from typing import TypeVar
from uuid import UUID

K = TypeVar("K")
V = TypeVar("V")


def is_uuid(value: str) -> bool:
    """
    >>> is_uuid('7ca42f43-8bd9-4a26-acb8-cb756f42bebb')
    True
    >>> is_uuid('226')
    False

    """
    try:
        UUID(value)
    except ValueError:
        return False
    return True


def projection(
    m: Mapping[K, V], keys: list[K], default: V | None = None
) -> dict[K, V | None]:
    """
    Extract a subset of key:value pairs from a mapping into a new dictionary.
    >>> projection({'a': 1, 'b': 2}, ['a'])
    {'a': 1}

    """
    return {k: m.get(k, default) for k in keys}
