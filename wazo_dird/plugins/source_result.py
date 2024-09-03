# Copyright 2014-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
import string
from typing import Any

logger = logging.getLogger(__name__)


class _NoErrorFormatter(string.Formatter):
    def format(self, format_string, *args, **kwargs):
        try:
            return super().format(format_string, *args, **kwargs).strip()
        except Exception as e:
            logger.debug(
                'skipping string formatting %s %s: %s',
                format_string,
                e.__class__.__name__,
                e,
            )
            return None

    def get_value(self, key, args, kwargs):
        if isinstance(key, str):
            value = kwargs.get(key)
            if value is None:
                return ''
            return value

        return super().get_value(key, args, kwargs)


class _SourceResult:
    _unique_column: str | None = None
    backend: str
    source: str
    _format_columns: dict[str, str] = {}

    fields: dict[str, Any | None]
    relations: dict[str, Any | None]

    def __init__(
        self,
        fields,
        xivo_id=None,
        agent_id=None,
        user_id=None,
        user_uuid=None,
        endpoint_id=None,
    ):
        self._formatter = _NoErrorFormatter()
        self.fields = dict(fields)
        source_entry_id = self.get_unique() if self._unique_column else None
        self.relations = {
            'xivo_id': xivo_id,
            'agent_id': agent_id,
            'user_id': user_id,
            'user_uuid': user_uuid,
            'endpoint_id': endpoint_id,
            'source_entry_id': source_entry_id,
        }

        self._add_formatted_columns()

    def get_unique(self):
        assert self._unique_column
        try:
            return str(self.fields[self._unique_column])
        except KeyError:
            logger.error(
                '"%s" is not properly configured, the unique column "%s" '
                'is not part of the result',
                self.source,
                self._unique_column,
            )
        return None

    def source_entry_id(self):
        return self.relations['source_entry_id']

    def _add_formatted_columns(self):
        for column, format_string in self._format_columns.items():
            value = self._formatter.format(format_string, **self.fields) or None
            self.fields[column] = value

    def __eq__(self, other):
        return (
            self.source == other.source
            and self.fields == other.fields
            and self.relations == other.relations
        )

    def __ne__(self, other):
        return not self == other

    def __repr__(self) -> str:
        data = ', '.join(
            str(datum)
            for datum in (
                self.fields,
                self.relations['xivo_id'],
                self.relations['agent_id'],
                self.relations['user_id'],
                self.relations['user_uuid'],
                self.relations['endpoint_id'],
            )
        )
        return f'{self.__class__.__name__}({data})'


def make_result_class(
    source_backend: str,
    source_name: str,
    unique_column: str | None = None,
    format_columns: dict[str, str] | None = None,
    is_deletable: bool = False,
    is_personal: bool = False,
) -> type[_SourceResult]:
    unique_column = (
        unique_column if unique_column is not None else _SourceResult._unique_column
    )
    format_columns = (
        format_columns if format_columns is not None else _SourceResult._format_columns
    )
    is_deletable_ = is_deletable
    is_personal_ = is_personal

    class SourceResult(_SourceResult):
        source = source_name
        backend = source_backend
        _unique_column = unique_column
        _format_columns = format_columns  # type: ignore
        is_deletable = is_deletable_
        is_personal = is_personal_

    return SourceResult
