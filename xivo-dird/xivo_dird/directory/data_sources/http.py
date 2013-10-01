# -*- coding: utf-8 -*-

# Copyright (C) 2007-2013 Avencall
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

import urllib
import urllib2
from itertools import imap
from xivo_dird.directory.data_sources.directory_data_source import DirectoryDataSource


class HTTPDirectoryDataSource(DirectoryDataSource):

    def __init__(self, base_uri, delimiter, key_mapping):
        self._base_uri = base_uri
        self._delimiter = delimiter
        self._key_mapping = key_mapping

    def lookup(self, string, fields, contexts=None):
        uri = self._build_uri(string, fields)
        fobj = urllib2.urlopen(uri)
        try:
            charset = self._get_result_charset(fobj)
            try:
                line = fobj.next()
            except StopIteration:
                raise ValueError('no lines in result from %s', uri)
            else:
                line = line.decode(charset).rstrip()
                headers = line.split(self._delimiter)
                map_fun = self._new_map_function(headers, charset)
                def generator():
                    try:
                        for result in imap(map_fun, fobj):
                            yield result
                    finally:
                        fobj.close()
                return generator()
        except Exception:
            fobj.close()
            raise

    def _build_uri(self, string, fields):
        uri = self._base_uri
        if uri[8:].find('/') == -1:
            uri += '/'
        encoded_string = urllib.quote(string.encode('UTF-8'))
        uri += '?' + '&'.join(field + '=' + encoded_string for field in fields)
        return uri

    def _get_result_charset(self, fobj):
        charset = 'UTF-8'
        content_type = fobj.info().getheader('Content-Type')
        if content_type:
            i = content_type.lower().find('charset=')
            if i >= 0:
                charset = content_type[i:].split(' ', 1)[0].split('=', 1)[1]
        return charset

    def _new_map_function(self, headers, charset):
        headers_map = dict((header, idx) for (idx, header) in enumerate(headers))
        mapping = [(std_key, headers_map[src_key]) for (std_key, src_key) in
                   self._key_mapping.iteritems() if
                   src_key in headers_map]
        def aux(line):
            line = line.decode(charset).rstrip()
            tokens = line.split(self._delimiter)
            return dict((std_key, tokens[idx]) for (std_key, idx) in mapping)
        return aux

    @classmethod
    def new_from_contents(cls, contents):
        base_uri = contents['uri']
        delimiter = contents.get('delimiter', ',')
        key_mapping = cls._get_key_mapping(contents)
        return cls(base_uri, delimiter, key_mapping)
