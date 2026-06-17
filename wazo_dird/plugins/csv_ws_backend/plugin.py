# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import csv
import logging
from collections.abc import Iterator
from typing import Any

import requests
from requests import RequestException

from wazo_dird import BaseSourcePlugin, make_result_class
from wazo_dird.helpers import BaseBackendView
from wazo_dird.plugins.base_plugins import SourceConfig, SourcePluginDependencies
from wazo_dird.plugins.source_result import _SourceResult as SourceResult

from . import http

logger = logging.getLogger(__name__)


class Config(SourceConfig, total=False):
    list_url: str
    lookup_url: str
    unique_column: str
    timeout: float
    delimiter: str
    verify_certificate: bool | str


class Dependencies(SourcePluginDependencies):
    config: Config  # type: ignore[misc]


class CSVWSView(BaseBackendView):
    backend = 'csv_ws'
    list_resource = http.CSVWSList
    item_resource = http.CSVWSItem


class CSVWSPlugin(BaseSourcePlugin):
    def load(self, config: Dependencies) -> None:  # type: ignore[override]
        logger.debug('Loading with %s', config)

        source_config = config['config']
        self._name = source_config['name']
        self._list_url = source_config.get('list_url')
        self._lookup_url = source_config['lookup_url']
        self._first_matched_columns = source_config.get('first_matched_columns', [])
        self._searched_columns = source_config.get('searched_columns', [])
        self._unique_column = source_config.get('unique_column')
        backend = source_config.get('backend', '')
        self._SourceResult = make_result_class(
            backend,
            source_config['name'],
            self._unique_column,
            source_config.get('format_columns', {}),
        )
        self._timeout = source_config.get('timeout', 10)
        self._delimiter = source_config.get('delimiter', ',')
        self._verify_certificate = source_config.get('verify_certificate', True)
        self._reader = _CSVReader(self._delimiter)

    def search(
        self, term: str, args: dict[str, Any] | None = None
    ) -> list[SourceResult]:
        logger.debug('Searching CSV WS `%s` with `%s`', self._name, term)
        url = self._lookup_url
        params = {column: term for column in self._searched_columns}

        try:
            response = requests.get(
                url,
                params=params,
                timeout=self._timeout,
                verify=self._verify_certificate,
            )
        except RequestException as e:
            logger.error('Error connecting to %s: %s', url, e)
            return []

        if response.status_code != 200:
            logger.debug('GET %s %s', url, response.status_code)
            return []

        return [
            self._SourceResult(result)
            for result in self._reader.from_text(response.text)
            if result
        ]

    def first_match(
        self, term: str, args: dict[str, Any] | None = None
    ) -> SourceResult | None:
        logger.debug('First matching CSV WS `%s` with `%s`', self._name, term)
        url = self._lookup_url
        params = {column: term for column in self._first_matched_columns}

        try:
            response = requests.get(
                url,
                params=params,
                timeout=self._timeout,
                verify=self._verify_certificate,
            )
        except RequestException as e:
            logger.error('Error connecting to %s: %s', url, e)
            return None

        if response.status_code != 200:
            logger.debug('GET %s %s', url, response.status_code)
            return None

        for result in self._reader.from_text(response.text):
            for column in self._first_matched_columns:
                if term == result.get(column):
                    return self._SourceResult(result)
        return None

    def list(
        self, source_entry_ids: list[str], args: dict[str, Any] | None = None
    ) -> list[SourceResult]:
        logger.debug(
            'Listing contacts %s from CSV WS `%s`', source_entry_ids, self._name
        )
        unique_column = self._unique_column
        if not (unique_column and self._list_url):
            return []

        try:
            response = requests.get(
                self._list_url, timeout=self._timeout, verify=self._verify_certificate
            )
        except RequestException as e:
            logger.error('Error connecting to %s: %s', self._list_url, e)
            return []

        if response.status_code != 200:
            return []

        return [
            self._SourceResult(result)
            for result in self._reader.from_text(response.text)
            if result.get(unique_column) in source_entry_ids
        ]


class _CSVReader:
    def __init__(self, delimiter: str) -> None:
        self._delimiter = delimiter

    def from_text(self, raw: str) -> Iterator[dict[str, str]]:
        reader = unicode_csv_reader(raw, delimiter=self._delimiter)
        headers = next(reader)
        for result in reader:
            yield dict(zip(headers, result))


def unicode_csv_reader(unicode_data: str, **kwargs: Any) -> Iterator[list[str]]:
    csv_reader = csv.reader(unicode_data.split('\n'), **kwargs)
    yield from csv_reader
