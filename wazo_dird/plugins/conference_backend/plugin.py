# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from unidecode import unidecode
from requests import HTTPError

from wazo_dird import BaseSourcePlugin, make_result_class
from wazo_dird.helpers import BaseBackendView
from wazo_dird.plugin_helpers.confd_client_registry import registry

from . import http

logger = logging.getLogger(__name__)


class ConferenceViewPlugin(BaseBackendView):
    backend = 'conference'
    list_resource = http.ConferenceList
    item_resource = http.ConferenceItem
    contact_list_resource = http.ConferenceContactList

    def load(self, dependencies):
        super().load(dependencies)
        api = dependencies['api']
        source_service = dependencies['services']['source']

        api.add_resource(
            self.contact_list_resource,
            '/backends/conference/sources/<source_uuid>/contacts',
            resource_class_args=(source_service,),
        )

    def unload(self):
        registry.unregister_all()


class ConferencePlugin(BaseSourcePlugin):
    def __init__(self):
        self._client = None
        self._uuid = None

    def load(self, dependencies):
        config = dependencies['config']
        self._searched_columns = config.get(self.SEARCHED_COLUMNS, [])
        self._first_matched_columns = config.get(self.FIRST_MATCHED_COLUMNS, [])
        self.name = config['name']
        self._client = registry.get(config)

        self._SourceResult = make_result_class(
            'conference',
            self.name,
            'id',
            format_columns=config.get(self.FORMAT_COLUMNS),
        )
        logger.info('Wazo %s successfully loaded', config['name'])

    def unload(self):
        registry.unregister_all()

    def list(self, unique_ids, args=None):
        logger.debug('Listing all conferences')
        contacts = self._fetch_contacts()
        matching_contacts = (c for c in contacts if str(c['id']) in unique_ids)
        results = [self._SourceResult(c) for c in matching_contacts]
        logger.debug('Found %s conferences', len(results))
        return results

    def search(self, term, profile=None, args=None):
        logger.debug('Looking for all conferences matching "%s"', term)
        clean_term = unidecode(term.lower())
        contacts = self._fetch_contacts()
        matching_contacts = (c for c in contacts if self._search_filter(clean_term, c))
        results = [self._SourceResult(c) for c in matching_contacts]
        logger.debug('Found %s conferences', len(results))
        return results

    def first_match(self, term, args=None):
        logger.debug('Looking for first conference matching "%s"', term)
        lowered_term = term.lower()
        for contact in self._fetch_contacts():
            if self._first_match_filter(lowered_term, contact):
                logger.debug('Found one conference')
                return self._SourceResult(contact)
        logger.debug('Found no conference')

    def match_all(self, terms, args=None):
        logger.debug('Looking for conference matching "%s"', terms)
        results = {}
        for contact in self._fetch_contacts():
            for term in terms:
                lowered_term = term.lower()
                if self._first_match_filter(lowered_term, contact):
                    results[term] = self._SourceResult(contact)
                    logger.debug('Found one conference match to "%s"', term)

        if not results:
            logger.debug('Found no conference')
        return results

    def _first_match_filter(self, lowered_term, contact):
        for column in self._first_matched_columns:
            column_value = contact.get(column) or ''
            if isinstance(column_value, str):
                if lowered_term == column_value.lower():
                    return True
            elif isinstance(column_value, list):
                for item in column_value:
                    if lowered_term == item.lower():
                        return True

        return False

    def _search_filter(self, clean_term, contact):
        for column in self._searched_columns:
            column_value = contact.get(column) or ''
            if isinstance(column_value, str):
                clean_column_value = unidecode(column_value.lower())
                if clean_term in clean_column_value:
                    return True
            elif isinstance(column_value, list):
                for item in column_value:
                    clean_item = unidecode(item.lower())
                    if clean_term in clean_item:
                        return True

        return False

    def _fetch_contacts(self):
        if not self._client:
            logger.info('conference source not initialized properly %s', self.name)
            return

        try:
            response = self._client.conferences.list()
        except HTTPError as e:
            logger.info('failed to fetch conferences %s', e)
            return

        for conference in response['items']:
            extensions = []
            for extension in conference['extensions']:
                extensions.append(extension['exten'])
            incalls = []
            for incall in conference['incalls']:
                for extension in incall['extensions']:
                    incalls.append(extension['exten'])

            yield {
                'id': conference['id'],
                'name': conference['name'],
                'extensions': extensions,
                'incalls': incalls,
            }
