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


class _SourceResult(object):

    _unique_column = None
    source = None
    _source_to_dest_map = {}

    def __init__(self, fields, xivo_id=None, agent_id=None, user_id=None, endpoint_id=None):
        self.fields = fields
        self.relations = {'xivo_id': xivo_id,
                          'agent_id': agent_id,
                          'user_id': user_id,
                          'endpoint_id': endpoint_id}

        self._add_destination_columns()

    def get_unique(self):
        return str(self.fields[self._unique_column])

    def _add_destination_columns(self):
        for source, destination in self._source_to_dest_map.iteritems():
            self.fields[destination] = self.fields.get(source)

    def __eq__(self, other):
        return (self.source == other.source
                and self.fields == other.fields
                and self.relations == other.relations)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        fields = ', '.join(repr(v) for v in self.fields.values())
        return '<%s(%s)%s>' % (self.__class__.__name__, fields, self.relations)


def make_result_class(source_name, unique_column=None, source_to_dest_map=None):
    if not unique_column:
        unique_column = _SourceResult._unique_column
    if not source_to_dest_map:
        source_to_dest_map = _SourceResult._source_to_dest_map

    class SourceResult(_SourceResult):
        source = source_name
        _unique_column = unique_column
        _source_to_dest_map = source_to_dest_map

    return SourceResult
