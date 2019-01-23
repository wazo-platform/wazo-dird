# Copyright 2014-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from requests.exceptions import ConnectionError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from xivo.config_helper import parse_config_file
from xivo.token_renewer import TokenRenewer
from xivo_auth_client import Client as AuthClient
from xivo_confd_client import Client as ConfdClient

from wazo_dird import (
    BaseSourcePlugin,
    BaseViewPlugin,
    database,
    make_result_class,
)

from . import (
    http,
    services,
)

logger = logging.getLogger(__name__)


class WazoUserView(BaseViewPlugin):

    def load(self, dependencies):
        api = dependencies['api']
        config = dependencies['config']

        db_uri = config['db_uri']
        engine = create_engine(db_uri)
        Session = scoped_session(sessionmaker())
        Session.configure(bind=engine)
        crud = database.SourceCRUD(Session)
        wazo_backend_service = services.WazoBackendService(crud)

        api.add_resource(
            http.SourceList,
            '/backends/wazo/sources',
            resource_class_args=(wazo_backend_service, config['auth']),
        )
        api.add_resource(
            http.SourceItem,
            '/backends/wazo/sources/<source_uuid>',
            resource_class_args=(wazo_backend_service, config['auth']),
        )


class WazoUserPlugin(BaseSourcePlugin):

    _valid_keys = ['id', 'exten', 'firstname', 'lastname', 'userfield', 'email',
                   'description', 'mobile_phone_number', 'voicemail_number']

    def __init__(self, ConfdClientClass=ConfdClient, AuthClientClass=AuthClient):
        self._AuthClientClass = AuthClientClass
        self._ConfdClientClass = ConfdClientClass
        self._client = None
        self._uuid = None
        self._search_params = {'view': 'directory', 'recurse': True}

    def load(self, dependencies):
        config = dependencies['config']
        self._searched_columns = config.get(self.SEARCHED_COLUMNS, [])
        self._first_matched_columns = config.get(self.FIRST_MATCHED_COLUMNS, [])
        self.name = config['name']

        auth_config = dict(config['auth'])
        if auth_config.get('key_file'):
            # File must be readable by wazo-dird
            key_file = parse_config_file(auth_config.pop('key_file'))
            auth_config['username'] = key_file['service_id']
            auth_config['password'] = key_file['service_key']
        auth_client = self._AuthClientClass(**auth_config)
        self._token_renewer = TokenRenewer(auth_client)

        confd_config = config['confd']
        logger.debug('confd config %s', confd_config)
        self._client = self._ConfdClientClass(**confd_config)

        self._SourceResult = make_result_class(
            self.name, 'id',
            format_columns=config.get(self.FORMAT_COLUMNS))

        self._search_params.update(config.get('extra_search_params', {}))

        self._token_renewer.subscribe_to_token_change(self._on_new_token)
        self._token_renewer.start()

        logger.info('Wazo %s successfully loaded', config['name'])

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
        except ConnectionError as e:
            logger.info('%s', e)
            return []
        except Exception as e:
            response = getattr(e, 'response', None)
            status_code = getattr(response, 'status_code', None)
            logger.info(
                'Cannot fetch UUID status_code "%s". No results will be returned',
                status_code,
            )
            return []

        try:
            entries = self._fetch_users(term)
        except ConnectionError as e:
            logger.info('%s', e)
            return []
        except Exception as e:
            response = getattr(e, 'response', None)
            status_code = getattr(response, 'status_code', None)

            logger.info(
                'Cannot fetch entries status_code "%s". No results will be returned',
                status_code,
            )
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
