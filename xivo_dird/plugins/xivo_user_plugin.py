# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2016 Avencall
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

    _valid_keys = ['id', 'exten', 'firstname', 'lastname', 'userfield', 'email',
                   'description', 'mobile_phone_number', 'voicemail_number']

    def __init__(self, ConfdClientClass=Client):
        self._ConfdClientClass = ConfdClientClass
        self._client = None
        self._uuid = None
        self._search_params = {'view': 'directory'}

    def load(self, args):
        self._searched_columns = args['config'].get(self.SEARCHED_COLUMNS, [])
        self._first_matched_columns = args['config'].get(self.FIRST_MATCHED_COLUMNS, [])
        self.name = args['config']['name']

        confd_config = args['config']['confd_config']
        logger.debug('confd config %s', confd_config)
        self._client = self._ConfdClientClass(**confd_config)

        self._SourceResult = make_result_class(
            self.name, 'id',
            format_columns=args['config'].get(self.FORMAT_COLUMNS))

        self._search_params.update(args['config'].get('extra_search_params', {}))

        logger.info('XiVO %s successfully loaded', args['config']['name'])

    def name(self):
        return self.name

    def search(self, term, profile=None, args=None):
        lowered_term = term.lower()
        entries = self._fetch_entries(term)

        def match_fn(entry):
            for column in self._searched_columns:
                if lowered_term in unicode(entry.fields.get(column, '')).lower():
                    return True
            return False

        return [entry for entry in entries if match_fn(entry)]

    def first_match(self, term, args=None):
        entries = self._fetch_entries(term)

        def match_fn(entry):
            for column in self._first_matched_columns:
                if term == entry.fields.get(column):
                    return True
            return False

        for entry in entries:
            if match_fn(entry):
                return entry
        return None

    def list(self, unique_ids, args=None):
        entries = self._fetch_entries()

        def match_fn(entry):
            for unique_id in unique_ids:
                if unique_id == entry.get_unique():
                    return True
            return False

        return [entry for entry in entries if match_fn(entry)]

    def _fetch_entries(self, term=None):
        try:
            uuid = self._get_uuid()
        except Exception:
            logger.exception('Cannot fetch UUID. No results will be returned')
            return []

        try:
            entries = self._fetch_users(term)
        except Exception:
            logger.exception('Cannot fetch entries. No results will be returned')
            return []

        return (self._source_result_from_entry(entry, uuid)
                for entry in entries)

    def _get_uuid(self):
        if self._uuid:
            return self._uuid

        infos = self._client.infos()
        self._uuid = infos['uuid']
        return self._uuid

    def _fetch_users(self, term=None):
        search_params = dict(self._search_params)
        if term:
            search_params['search'] = term
        users = self._client.users.list(**search_params)
        return (user for user in users['items'])

    def _source_result_from_entry(self, entry, uuid):
        return self._SourceResult({key: entry.get(key) for key in self._valid_keys},
                                  xivo_id=uuid,
                                  agent_id=entry['agent_id'],
                                  user_id=entry['id'],
                                  endpoint_id=entry['line_id'])
