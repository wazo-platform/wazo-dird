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
import StringIO

from xivo_dird import BaseSourcePlugin
from xivo_dird import make_result_class

logger = logging.getLogger(__name__)


class CSVWSPlugin(BaseSourcePlugin):

    def load(self, config):
        logger.debug('Loading with %s', config)

        self._lookup_url = config['config']['lookup_url']
        self._SourceResult = make_result_class(
            config['config']['name'],
            config['config'].get(self.UNIQUE_COLUMN),
            config['config'].get(self.SOURCE_TO_DISPLAY, {}))
        self._delimiter = config['config'].get('delimiter', ',')
        self._reader = _CSVReader(self._delimiter)

    def search(self, term, profile=None, args=None):
        url = self._lookup_url.format(term=term)

        response = requests.get(url, timeout=5)

        if response.status_code != 200:
            return

        for result in self._reader.from_text(response.text):
            yield self._SourceResult(result)


class _CSVReader(object):

    def __init__(self, delimiter):
        self._delimiter = delimiter

    def from_text(self, raw):
        file_object = StringIO.StringIO(raw)
        reader = csv.reader(file_object, delimiter=self._delimiter)
        headers = next(reader)
        for result in reader:
            yield dict(zip(headers, result))
