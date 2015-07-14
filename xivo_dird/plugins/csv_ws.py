# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import csv
import logging
import requests

from itertools import izip
from xivo_dird import BaseSourcePlugin
from xivo_dird import make_result_class

logger = logging.getLogger(__name__)


class CSVWSPlugin(BaseSourcePlugin):

    def load(self, config):
        logger.debug('Loading with %s', config)

        self._list_url = config['config'].get('list_url')
        self._lookup_url = unicode(config['config']['lookup_url'])
        self._unique_column = config['config'].get(self.UNIQUE_COLUMN)
        self._SourceResult = make_result_class(
            config['config']['name'],
            self._unique_column,
            config['config'].get(self.SOURCE_TO_DISPLAY, {}))
        self._timeout = config['config'].get('timeout', 10)
        self._delimiter = config['config'].get('delimiter', ',')
        self._reader = _CSVReader(self._delimiter)

    def search(self, term, profile=None, args=None):
        url = self._lookup_url.format(term=term)

        response = requests.get(url, timeout=self._timeout)

        if response.status_code != 200:
            return []

        return [self._SourceResult(result)
                for result in self._reader.from_text(response.text)]

    def list(self, source_entry_ids):
        if not (self._unique_column and self._list_url):
            return []

        response = requests.get(self._list_url, timeout=self._timeout)

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
            yield dict(izip(headers, result))


def unicode_csv_reader(unicode_data, **kwargs):
    csv_reader = csv.reader(utf_8_encoder(unicode_data), **kwargs)
    for row in csv_reader:
        yield [unicode(field, 'utf-8') for field in row]


def utf_8_encoder(unicode_data):
    encoded_data = unicode_data.encode('utf-8')
    for line in encoded_data.split('\n'):
        yield line
