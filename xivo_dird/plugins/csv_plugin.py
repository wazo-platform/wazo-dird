# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Avencall
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

from itertools import ifilter
from itertools import izip
from functools import partial
from xivo_dird import BaseSourcePlugin
from xivo_dird import make_result_class

logger = logging.getLogger(__name__)


class CSVPlugin(BaseSourcePlugin):
    '''The CSVPlugin sources will load a file containing CSV entries
    and search through the entries according to the configuration file.

    The following values are required in the configuration:

       {'file': <path/to/the/csv/file>,
        'searched_columns': ['column_1', 'column_2', ..., 'column_n']}

    The `file` is the file that should be read by the plugin
    The `searched_columns` are the columns used to search for a term
    '''

    def load(self, args):
        if 'config' not in args:
            logger.warning('Missing config in startup arguments: %s', args)

        self._config = args.get('config', {})
        self._name = self._config.get('name', '')
        self._content = []
        self._has_unique_id = not len(self._config.get(self.UNIQUE_COLUMNS, [])) == 0
        self._load_file()
        self._SourceResult = make_result_class(self._name,
                                               self._config.get(self.UNIQUE_COLUMNS, []),
                                               self._config.get('source_to_display', {}))

    def name(self):
        return self._name

    def search(self, term, args=None):
        if 'searched_columns' not in self._config:
            return []

        fn = partial(self._low_case_match_entry, term.lower(), self._config[self.SEARCHED_COLUMNS])
        return self._list_from_predicate(fn)

    def list(self, unique_ids):
        if not self._has_unique_id:
            return []

        fn = partial(self._is_in_unique_ids, unique_ids)
        return self._list_from_predicate(fn)

    def _load_file(self):
        if 'file' not in self._config:
            logger.warning('Could not initialize missing file configuration')
            return

        try:
            with open(self._config['file'], 'r') as f:
                csvreader = csv.reader(f, delimiter=self._config.get('separator', ','))
                keys = [key.decode('utf-8') for key in next(csvreader)]
                self._content = [self._row_to_dict(keys, row) for row in csvreader]
        except IOError:
            logger.exception('Could not load CSV file content')

    def _list_from_predicate(self, predicate):
        return map(self._SourceResult, ifilter(predicate, self._content))

    def _is_in_unique_ids(self, unique_ids, entry):
        return self._make_unique(entry) in unique_ids

    def _low_case_match_entry(self, term, columns, entry):
        values = (entry[col].lower() for col in columns if col)
        for value in values:
            if term in value:
                return True
        return False

    @staticmethod
    def _row_to_dict(keys, values):
        return dict(izip(
            keys, [value.decode('utf-8') if type(value) == str else value for value in values]))

    def _make_unique(self, entry):
        return tuple(entry[col] for col in self._config[self.UNIQUE_COLUMNS])
