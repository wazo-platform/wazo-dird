# Copyright 2014-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from wazo_dird import BaseSourcePlugin
from wazo_dird import make_result_class
from xivo_auth_client import Client as AuthClient
from xivo_confd_client import Client as ConfdClient
from xivo.token_renewer import TokenRenewer

logger = logging.getLogger(__name__)


class XivoUserPlugin(BaseSourcePlugin):

    _valid_keys = ['id', 'exten', 'firstname', 'lastname', 'userfield', 'email',
                   'description', 'mobile_phone_number', 'voicemail_number']

    def __init__(self, ConfdClientClass=ConfdClient):
        self._ConfdClientClass = ConfdClientClass
        self._client = None
        self._uuid = None
        self._search_params = {'view': 'directory'}

    def load(self, args):
        self._searched_columns = args['config'].get(self.SEARCHED_COLUMNS, [])
        self._first_matched_columns = args['config'].get(self.FIRST_MATCHED_COLUMNS, [])
        self.name = args['config']['name']

        auth_config = args['config']['auth']
        auth_client = AuthClient(**auth_config)
        self._token_renewer = TokenRenewer(auth_client)

        confd_config = args['config']['confd']
        logger.debug('confd config %s', confd_config)
        self._client = self._ConfdClientClass(**confd_config)

        self._SourceResult = make_result_class(
            self.name, 'id',
            format_columns=args['config'].get(self.FORMAT_COLUMNS))

        self._search_params.update(args['config'].get('extra_search_params', {}))

        self._token_renewer.subscribe_to_token_change(self._on_new_token)
        self._token_renewer.start()

        logger.info('XiVO %s successfully loaded', args['config']['name'])

    def unload(self):
        token_renewer = getattr(self, '_token_renewer', None)
        if not token_renewer:
            return

        logger.info('stopping token renewer')
        token_renewer.stop()

    def name(self):
        return self.name

    def search(self, term, profile=None, args=None):
        lowered_term = term.lower()
        entries = self._fetch_entries(term)

        def match_fn(entry):
            for column in self._searched_columns:
                column_value = entry.fields.get(column) or ''
                if lowered_term in str(column_value).lower():
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

    def _on_new_token(self, token):
        logger.debug('new token received')
        self._client.set_token(token)

    def _source_result_from_entry(self, entry, uuid):
        return self._SourceResult({key: entry.get(key) for key in self._valid_keys},
                                  xivo_id=uuid,
                                  agent_id=entry['agent_id'],
                                  user_id=entry['id'],
                                  user_uuid=entry['uuid'],
                                  endpoint_id=entry['line_id'])
