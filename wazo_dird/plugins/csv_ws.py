# -*- coding: utf-8 -*-
# Copyright 2015-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import csv
import logging
import requests

from requests import RequestException
from wazo_dird import BaseSourcePlugin
from wazo_dird import make_result_class

logger = logging.getLogger(__name__)


class CSVWSPlugin(BaseSourcePlugin):

    def load(self, config):
        logger.debug('Loading with %s', config)

        self._name = config['config']['name']
        self._list_url = config['config'].get('list_url')
        self._lookup_url = config['config']['lookup_url']
        self._first_matched_columns = config['config'].get(self.FIRST_MATCHED_COLUMNS, [])
        self._searched_columns = config['config'].get(self.SEARCHED_COLUMNS, [])
        self._unique_column = config['config'].get(self.UNIQUE_COLUMN)
        self._SourceResult = make_result_class(
            config['config']['name'],
            self._unique_column,
            config['config'].get(self.FORMAT_COLUMNS, {}))
        self._timeout = config['config'].get('timeout', 10)
        self._delimiter = config['config'].get('delimiter', ',')
        self._verify_certificate = config['config'].get('verify_certificate', True)
        self._reader = _CSVReader(self._delimiter)

    def search(self, term, args=None):
        logger.debug('Searching CSV WS `%s` with `%s`', self._name, term)
        url = self._lookup_url
        params = {column: term for column in self._searched_columns}

        try:
            response = requests.get(url, params=params, timeout=self._timeout, verify=self._verify_certificate)
        except RequestException as e:
            logger.error('Error connecting to %s: %s', url, e)
            return []

        if response.status_code != 200:
            logger.debug('GET %s %s', url, response.status_code)
            return []

        return [self._SourceResult(result)
                for result in self._reader.from_text(response.text)
                if result]

    def first_match(self, term, args=None):
        logger.debug('First matching CSV WS `%s` with `%s`', self._name, term)
        url = self._lookup_url
        params = {column: term for column in self._first_matched_columns}

        try:
            response = requests.get(url, params=params, timeout=self._timeout, verify=self._verify_certificate)
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

    def list(self, source_entry_ids, args=None):
        logger.debug('Listing contacts %s from CSV WS `%s`', source_entry_ids, self._name)
        if not (self._unique_column and self._list_url):
            return []

        try:
            response = requests.get(self._list_url, timeout=self._timeout, verify=self._verify_certificate)
        except RequestException as e:
            logger.error('Error connecting to %s: %s', self._list_url, e)
            return []

        if response.status_code != 200:
            return []

        return [self._SourceResult(result)
                for result in self._reader.from_text(response.text)
                if result.get(self._unique_column) in source_entry_ids]


class _CSVReader(object):

    def __init__(self, delimiter):
        self._delimiter = delimiter

    def from_text(self, raw):
        reader = unicode_csv_reader(raw, delimiter=self._delimiter)
        headers = next(reader)
        for result in reader:
            yield dict(zip(headers, result))


def unicode_csv_reader(unicode_data, **kwargs):
    csv_reader = csv.reader(unicode_data.split('\n'), **kwargs)
    for row in csv_reader:
        yield row
