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

import logging

from xivo_dird import BaseSourcePlugin
from xivo_dird import make_result_class
from xivo_confd_client import Client

logger = logging.getLogger(__name__)


class XivoUserPlugin(BaseSourcePlugin):

    def __init__(self, ConfdClientClass=Client):
        self._ConfdClientClass = ConfdClientClass
        self._uuid = None
        self._initialized = False

    def load(self, args):
        self._confd_config = args['config']['confd_config']
        logger.debug('confd config %s', self._confd_config)
        self._searched_columns = args['config'].get(self.SEARCHED_COLUMNS, [])
        self.name = args['config']['name']
        self._entries = []
        self._SourceResult = make_result_class(
            self.name, ['id'],
            source_to_dest_map=args['config'].get(self.SOURCE_TO_DISPLAY))
        self._fetch_content()

    def name(self):
        return self.name

    def search(self, term, profile, args=None):
        self._fetch_content()
        lowered_term = term.lower()

        def match_fn(entry):
            for column in self._searched_columns:
                if lowered_term in unicode(entry.fields.get(column, '')).lower():
                    return True
            return False

        return [entry for entry in self._entries if match_fn(entry)]

    def list(self, unique_ids):
        self._fetch_content()

        def match_fn(entry):
            for unique_id in unique_ids:
                if unique_id == entry.get_unique():
                    return True
            return False

        return [entry for entry in self._entries if match_fn(entry)]

    def _fetch_content(self):
        if self._initialized:
            return

        try:
            self._uuid = self._fetch_uuid()
            users = self._fetch_users()
            self._entries = [self._source_result_from_entry(user) for user in users]
            self._initialized = True
            logger.info('XiVO %s successfully loaded.', self._uuid)
        except Exception:
            logger.debug('%s failed to load content, will retry later', self.name)

    def _fetch_uuid(self):
        client = self._ConfdClientClass(**self._confd_config)
        infos = client.infos()
        return infos['uuid']

    def _fetch_users(self):
        client = self._ConfdClientClass(**self._confd_config)
        users = client.users.list(view='directory')
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
