# -*- coding: utf-8 -*-

# Copyright (C) 2007-2014 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import urllib2
from itertools import ifilter, imap
import logging
from xivo.unicode_csv import UnicodeDictReader
from xivo_dird.directory.data_sources.directory_data_source import DirectoryDataSource

logger = logging.getLogger('csv directory')


class CSVFileDirectoryDataSource(DirectoryDataSource):

    def __init__(self, csv_file, delimiter, key_mapping):
        """
        csv_file -- the path to the CSV file
        delimiter -- the character used to separate fields in the CSV file
        key_mapping -- a dictionary mapping std key to list of CSV field name
        """
        self._csv_file = csv_file
        self._delimiter = delimiter.encode('UTF-8')  # binary input to the parser
        self._key_mapping = key_mapping

    def lookup(self, string, fields, contexts=None):
        """Do a lookup using string to match on the given list of src fields."""
        fobj = urllib2.urlopen(self._csv_file)
        try:
            reader = UnicodeDictReader(fobj, delimiter=self._delimiter)
            filter_fun = self._new_filter_function(string, fields,
                                                   reader.fieldnames)
            map_fun = self._new_map_function(reader.fieldnames)

            def generator():
                try:
                    for result in imap(map_fun, ifilter(filter_fun, reader)):
                        yield result
                finally:
                    fobj.close()
            # this function is not an iterator because we want the fail fast
            # behaviour that iterator/generator doesn't have
            return generator()
        except Exception:
            fobj.close()
            raise

    def _new_filter_function(self, string, requested_fields, available_fields):
        lookup_fields = list(set(available_fields).intersection(requested_fields))
        if not lookup_fields:
            logger.warning('Requested fields %s but only fields %s are available',
                           requested_fields, available_fields)
        lowered_string = string.lower()

        def aux(row):
            for field in lookup_fields:
                if lowered_string in row[field].lower():
                    return True
            return False
        return aux

    def _new_map_function(self, available_fields):
        mapping = list((std_key, src_key) for
                       (std_key, src_key) in self._key_mapping.iteritems() if
                       src_key in available_fields)
        if not mapping:
            logger.warning('Key mapping %s but only fields %s are available',
                           self._key_mapping, available_fields)

        def aux(row):
            return dict((std_key, row[src_key]) for (std_key, src_key) in mapping)
        return aux

    @classmethod
    def new_from_contents(cls, contents):
        """Return a new instance of this class from "configuration contents"
        and a ctiserver instance.
        """
        csv_file = contents['uri']
        delimiter = contents.get('delimiter', ',')
        key_mapping = cls._get_key_mapping(contents)
        return cls(csv_file, delimiter, key_mapping)
