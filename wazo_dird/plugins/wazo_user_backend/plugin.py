# Copyright 2014-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from requests.exceptions import ConnectionError

from wazo_dird import (
    BaseSourcePlugin,
    make_result_class,
)
from wazo_dird.helpers import BaseBackendView

from . import http
from .contact import registry

logger = logging.getLogger(__name__)


class WazoUserView(BaseBackendView):

    backend = 'wazo'
    list_resource = http.WazoList
    item_resource = http.WazoItem
    contact_list_resource = http.WazoContactList

    def load(self, dependencies):
        super().load(dependencies)
        api = dependencies['api']
        source_service = dependencies['services']['source']

        api.add_resource(
            self.contact_list_resource,
            "/backends/wazo/sources/<source_uuid>/contacts",
            resource_class_args=((source_service,)),
        )

    def unload(self):
        registry.unregister_all()


class WazoUserPlugin(BaseSourcePlugin):

    _valid_keys = ['id', 'exten', 'firstname', 'lastname', 'userfield', 'email',
                   'description', 'mobile_phone_number', 'voicemail_number']

    def __init__(self):
        self._client = None
        self._uuid = None
        self._search_params = {'view': 'directory', 'recurse': True}

    def load(self, dependencies):
        config = dependencies['config']
        self._searched_columns = config.get(self.SEARCHED_COLUMNS, [])
        self._first_matched_columns = config.get(self.FIRST_MATCHED_COLUMNS, [])
        self.name = config['name']
        self._client = registry.get(config)

        self._SourceResult = make_result_class(
            'wazo',
            self.name,
            'id',
            format_columns=config.get(self.FORMAT_COLUMNS),
        )
        self._search_params.update(config.get('extra_search_params', {}))
        logger.info('Wazo %s successfully loaded', config['name'])

    def unload(self):
        registry.unregister_all()

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

    def _source_result_from_entry(self, entry, uuid):
        return self._SourceResult({key: entry.get(key) for key in self._valid_keys},
                                  xivo_id=uuid,
                                  agent_id=entry['agent_id'],
                                  user_id=entry['id'],
                                  user_uuid=entry['uuid'],
                                  endpoint_id=entry['line_id'])
