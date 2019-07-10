# Copyright 2014-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import csv
import logging

from functools import partial
from wazo_dird import BaseSourcePlugin
from wazo_dird import make_result_class
from wazo_dird.helpers import BaseBackendView

from . import http

logger = logging.getLogger(__name__)


class CSVView(BaseBackendView):

    backend = 'csv'
    list_resource = http.CSVList
    item_resource = http.CSVItem


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
        self._has_unique_id = self._config.get(self.UNIQUE_COLUMN, None) is not None
        self._load_file()
        backend = self._config.get('backend', '')
        self._SourceResult = make_result_class(
            backend,
            self._name,
            self._config.get(self.UNIQUE_COLUMN, None),
            self._config.get(self.FORMAT_COLUMNS, {}),
        )

    def name(self):
        return self._name

    def search(self, term, args=None):
        if self.SEARCHED_COLUMNS not in self._config:
            return []

        fn = partial(
            self._low_case_match_entry,
            term.lower(),
            self._config[self.SEARCHED_COLUMNS],
        )
        return self._list_from_predicate(fn)

    def first_match(self, term, args=None):
        if self.FIRST_MATCHED_COLUMNS not in self._config:
            return None

        for entry in self._content:
            if self._exact_match_entry(
                term, self._config[self.FIRST_MATCHED_COLUMNS], entry
            ):
                return self._SourceResult(entry)
        return None

    def list(self, unique_ids, args=None):
        if not self._has_unique_id:
            return []

        fn = partial(self._is_in_unique_ids, unique_ids)
        return self._list_from_predicate(fn)

    def _load_file(self):
        if 'file' not in self._config:
            logger.warning('Could not initialize missing file configuration')
            return

        filename = self._config['file']
        delimiter = str(self._config.get('separator', ','))

        try:
            logger.debug('Reading %s with delimiter %r', filename, delimiter)
            with open(filename, 'r') as f:
                csvreader = csv.reader(f, delimiter=delimiter)
                keys = [key for key in next(csvreader)]
                self._content = [self._row_to_dict(keys, row) for row in csvreader]
                logger.debug('Loaded with %s', self._content)
        except IOError:
            logger.exception('Could not load CSV file content')

    def _list_from_predicate(self, predicate):
        return list(map(self._SourceResult, filter(predicate, self._content)))

    def _is_in_unique_ids(self, unique_ids, entry):
        return self._make_unique(entry) in unique_ids

    def _low_case_match_entry(self, term, columns, entry):
        logger.debug('Looking for %r in %s %s', term, entry, columns)
        values = (entry[col].lower() for col in columns if col)
        for value in values:
            if term in value:
                return True
        return False

    def _exact_match_entry(self, term, columns, entry):
        values = (entry[col] for col in columns if col)
        for value in values:
            if term == value:
                return True
        return False

    @staticmethod
    def _row_to_dict(keys, values):
        return dict(zip(keys, values))

    def _make_unique(self, entry):
        unique_column = self._config[self.UNIQUE_COLUMN]
        return entry[unique_column]
