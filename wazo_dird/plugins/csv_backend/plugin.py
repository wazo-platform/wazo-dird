# Copyright 2014-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import csv
import logging
import pathlib
from builtins import list as list_t
from collections.abc import Callable, Iterable
from functools import partial
from typing import Any, cast

from wazo_dird import BaseSourcePlugin, make_result_class
from wazo_dird.helpers import BaseBackendView
from wazo_dird.plugins.base_plugins import SourcePluginDependencies
from wazo_dird.plugins.source_result import _SourceResult as SourceResult

from . import http

logger = logging.getLogger(__name__)


class CSVView(BaseBackendView):
    backend = 'csv'
    list_resource = http.CSVList
    item_resource = http.CSVItem


class CSVPlugin(BaseSourcePlugin):
    """The CSVPlugin sources will load a file containing CSV entries
    and search through the entries according to the configuration file.

    The following values are required in the configuration:

       {'file': <path/to/the/csv/file>,
        'searched_columns': ['column_1', 'column_2', ..., 'column_n']}

    The `file` is the file that should be read by the plugin
    The `searched_columns` are the columns used to search for a term
    """

    def __init__(self) -> None:
        super().__init__()
        self._csv_last_modification_time: float | None = None
        self._config: dict[str, Any] = {}
        self._name: str = ''
        self._content: list_t[dict[str, Any]] = []
        self._has_unique_id: bool = False
        self._SourceResult: type[SourceResult]

    def load(self, args: SourcePluginDependencies) -> None:
        if 'config' not in args:
            logger.warning('Missing config in startup arguments: %s', args)

        self._config = cast('dict[str, Any]', args.get('config', {}))
        self._name = self._config.get('name', '')
        self._content = []
        self._has_unique_id = self._config.get(self.UNIQUE_COLUMN, None) is not None
        self._load_file()
        backend = self._config.get('backend', '')
        self._SourceResult = make_result_class(
            backend,
            self._name,
            self._config.get(self.UNIQUE_COLUMN, None),
            self._config.get(self.FORMAT_COLUMNS, {}),
        )

    def name(self) -> str:  # type: ignore[override]
        return self._name

    def search(
        self, term: str, args: dict[str, Any] | None = None
    ) -> list_t[SourceResult]:
        if self.SEARCHED_COLUMNS not in self._config:
            return []
        self._load_file()
        fn = partial(
            self._low_case_match_entry,
            term.lower(),
            self._config[self.SEARCHED_COLUMNS],
        )
        return self._list_from_predicate(fn)

    def first_match(
        self, term: str, args: dict[str, Any] | None = None
    ) -> SourceResult | None:
        logger.debug('Looking for the first CSV entry matching "%s"', term)
        self._load_file()
        if self.FIRST_MATCHED_COLUMNS not in self._config:
            logger.debug('No column configured for first match. Stopping.')
            return None

        for entry in self._content:
            if self._exact_match_entry(
                term, self._config[self.FIRST_MATCHED_COLUMNS], entry
            ):
                logger.debug('Found one CSV entry matching "%s"', term)
                return self._SourceResult(entry)
        logger.debug('Found no CSV entry matching "%s"', term)
        return None

    def list(
        self, unique_ids: list_t[str], args: dict[str, Any] | None = None
    ) -> list_t[SourceResult]:
        if not self._has_unique_id:
            return []
        self._load_file()
        fn = partial(self._is_in_unique_ids, unique_ids)
        return self._list_from_predicate(fn)

    def _load_file(self) -> None:
        if 'file' not in self._config:
            logger.warning('Could not initialize missing file configuration')
            return

        filename = self._config['file']
        delimiter = str(self._config.get('separator', ','))
        fname = pathlib.Path(filename)
        try:
            tmp_csv_file_last_modification_date = fname.stat().st_mtime
            if self._csv_last_modification_time == tmp_csv_file_last_modification_date:
                return
            try:
                logger.debug('Reading %s with delimiter %r', filename, delimiter)
                with open(filename) as f:
                    csvreader = csv.reader(f, delimiter=delimiter)
                    keys = [key for key in next(csvreader)]
                    self._content = [self._row_to_dict(keys, row) for row in csvreader]
                    logger.debug('Loaded with %s', self._content)
                self._csv_last_modification_time = tmp_csv_file_last_modification_date
            except OSError:
                logger.exception('Could not load CSV file content')
        except FileNotFoundError:
            logger.exception('Could not locate CSV file on the system')

    def _list_from_predicate(
        self, predicate: Callable[[dict[str, Any]], bool]
    ) -> list_t[SourceResult]:
        return list(map(self._SourceResult, filter(predicate, self._content)))

    def _is_in_unique_ids(self, unique_ids: list_t[str], entry: dict[str, Any]) -> bool:
        return self._make_unique(entry) in unique_ids

    def _low_case_match_entry(
        self, term: str, columns: list_t[str], entry: dict[str, Any]
    ) -> bool:
        logger.debug('Looking for %r in %s %s', term, entry, columns)
        lowered_values = [value.lower() for value in self._entry_values(columns, entry)]
        for value in lowered_values:
            if term in value:
                return True
        return False

    def _exact_match_entry(
        self, term: str, columns: list_t[str], entry: dict[str, Any]
    ) -> bool:
        for value in self._entry_values(columns, entry):
            if term == value:
                return True
        return False

    @staticmethod
    def _entry_values(
        column_names: Iterable[str], entry: dict[str, Any]
    ) -> list_t[Any]:
        values = []
        for column_name in column_names:
            if not column_name:
                continue
            try:
                values.append(entry[column_name])
            except KeyError:
                logger.info(
                    'plugin misconfigured "%s" is not in the CSV file',
                    column_name,
                )
        return values

    @staticmethod
    def _row_to_dict(keys: Iterable[str], values: Iterable[Any]) -> dict[str, Any]:
        return dict(zip(keys, values))

    def _make_unique(self, entry: dict[str, Any]) -> Any:
        unique_column = self._config[self.UNIQUE_COLUMN]
        return entry[unique_column]
