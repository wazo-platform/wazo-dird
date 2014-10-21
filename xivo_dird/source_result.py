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


class SourceResult(object):

    def __init__(self, fields, source, xivo_id=None, agent_id=None, user_id=None, endpoint_id=None):
        self.fields = fields
        self.source = source
        self.relations = {'agent': None,
                          'user': None,
                          'endpoint': None}

        if agent_id:
            self.relations['agent'] = {'id': agent_id,
                                       'xivo_id': xivo_id}

        if user_id:
            self.relations['user'] = {'id': user_id,
                                      'xivo_id': xivo_id}

        if endpoint_id:
            self.relations['endpoint'] = {'id': endpoint_id,
                                          'xivo_id': xivo_id}
