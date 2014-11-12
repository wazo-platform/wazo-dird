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

from xivo_dird import BaseSourcePlugin
from xivo_dird import make_result_class


class XivoUserPlugin(BaseSourcePlugin):

    def __init__(self, ConfdClientClass):
        # XXX add a default value to ConfdClientClass when the real client exists
        self._ConfdClientClass = ConfdClientClass

    def load(self, args):
        self._confd_url = args['config']['confd_url']
        self._searched_columns = args['config'].get(self.SEARCHED_COLUMNS, [])
        self.name = args['config']['name']
        self._entries = []
        self._SourceResult = make_result_class(
            self.name, ['id'],
            source_to_dest_map=args['config'].get(self.SOURCE_TO_DISPLAY))
        self._fetch_content()

    def name(self):
        return self.name

    def search(self, term):
        lowered_term = term.lower()

        def match_fn(entry):
            for column in self._searched_columns:
                if lowered_term in unicode(entry.fields.get(column, '')).lower():
                    return True
            return False

        return [entry for entry in self._entries if match_fn(entry)]

    def list(self, unique_ids):
        def match_fn(entry):
            for unique_id in unique_ids:
                if unique_id == entry.get_unique():
                    return True
            return False

        return [entry for entry in self._entries if match_fn(entry)]

    def _fetch_content(self):
        self._uuid = self._fetch_uuid()
        users = self._fetch_users()
        self._entries = [self._source_result_from_entry(user) for user in users]

    def _fetch_uuid(self):
        client = self._ConfdClientClass(self._confd_url)
        infos = client.get_infos()
        return infos['uuid']

    def _fetch_users(self):
        client = self._ConfdClientClass(self._confd_url)
        users = client.get_users(view='directory')
        return (user for user in users['items'])

    def _source_result_from_entry(self, entry):
        fields = {
            'id': entry['id'],
            'exten': entry.get('exten', ''),
            'firstname': entry.get('firstname', ''),
            'lastname': entry.get('lastname', ''),
            'mobile_phone_number': entry.get('mobile_phone_number', '')
        }
        return self._SourceResult(fields,
                                  xivo_id=self._uuid,
                                  agent_id=entry['agent_id'],
                                  user_id=entry['id'],
                                  endpoint_id=entry['line_id'])
