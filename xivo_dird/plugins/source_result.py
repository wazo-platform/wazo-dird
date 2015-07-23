# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2015 Avencall
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

import logging
import string

logger = logging.getLogger(__name__)


class _NoKeyErrorFormatter(string.Formatter):

    def format(self, format_string, *args, **kwargs):
        return super(_NoKeyErrorFormatter, self).format(format_string, *args, **kwargs).strip()

    def get_value(self, key, args, kwargs):
        if isinstance(key, str):
            value = kwargs.get(key)
            if value is None:
                return ''
            return value

        return super(_NoKeyErrorFormatter, self).get_value(key, args, kwargs)


class _SourceResult(object):

    _unique_column = None
    source = None
    _format_columns = {}

    def __init__(self, fields, xivo_id=None, agent_id=None, user_id=None, endpoint_id=None):
        self._formatter = _NoKeyErrorFormatter()
        self.fields = fields
        source_entry_id = self.get_unique() if self._unique_column else None
        self.relations = {'xivo_id': xivo_id,
                          'agent_id': agent_id,
                          'user_id': user_id,
                          'endpoint_id': endpoint_id,
                          'source_entry_id': source_entry_id}

        self._add_formatted_columns()

    def get_unique(self):
        try:
            return str(self.fields[self._unique_column])
        except KeyError:

            msg = '{source} is not properly configured, the unique column is not part of the result'.format(source=self.source)
            logger.exception(msg)
        return None

    def source_entry_id(self):
        return self.relations['source_entry_id']

    def _add_formatted_columns(self):
        for column, format_string in self._format_columns.iteritems():
            value = self._formatter.format(format_string, **self.fields) or None
            self.fields[column] = value

    def __eq__(self, other):
        return (self.source == other.source
                and self.fields == other.fields
                and self.relations == other.relations)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        fields = ', '.join(repr(v) for v in self.fields.values())
        return '<%s(%s)%s>' % (self.__class__.__name__, fields, self.relations)


def make_result_class(source_name, unique_column=None, format_columns=None, is_deletable=False, is_personal=False):
    if not unique_column:
        unique_column = _SourceResult._unique_column
    if not format_columns:
        format_columns = _SourceResult._format_columns

    class SourceResult(_SourceResult):
        source = source_name
        _unique_column = unique_column
        _format_columns = format_columns

    SourceResult.is_deletable = is_deletable
    SourceResult.is_personal = is_personal

    return SourceResult
