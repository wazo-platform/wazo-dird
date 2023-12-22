# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from wazo_dird import BaseSourcePlugin, database, make_result_class
from wazo_dird.database.helpers import Session
from wazo_dird.helpers import BaseBackendView

from . import http

logger = logging.getLogger(__name__)


class PersonalView(BaseBackendView):
    backend = 'personal'
    list_resource = http.PersonalList
    item_resource = http.PersonalItem


class PersonalBackend(BaseSourcePlugin):
    def load(self, config, search_engine=None):
        logger.debug('Loading personal source')

        unique_column = 'id'
        source_name = config['config']['name']
        format_columns = config['config'].get(self.FORMAT_COLUMNS, {})

        result_class = make_result_class(
            'personal',
            source_name,
            unique_column,
            format_columns,
            is_personal=True,
            is_deletable=True,
        )
        self._SourceResult = lambda contact: result_class(
            self._remove_empty_values(contact)
        )
        self._search_engine = search_engine or self._new_search_engine(
            config['config'].get(self.SEARCHED_COLUMNS),
            config['config'].get(self.FIRST_MATCHED_COLUMNS),
        )

    def search(self, term, args=None):
        logger.debug('Searching personal contacts with %s', term)
        user_uuid = args['user_uuid']
        matching_contacts = self._search_engine.find_personal_contacts(user_uuid, term)
        return self.format_contacts(matching_contacts)

    def first_match(self, term, args=None):
        logger.debug('First matching personal contacts with %s', term)
        user_uuid = args['user_uuid']
        matching_contacts = self._search_engine.find_first_personal_contact(
            user_uuid, term
        )
        for contact in self.format_contacts(matching_contacts):
            return contact

    def list(self, source_entry_ids, args):
        logger.debug('Listing personal contacts: %s', source_entry_ids)
        user_uuid = args['user_uuid']
        matching_contacts = self._search_engine.list_personal_contacts(
            user_uuid, source_entry_ids
        )
        return self.format_contacts(matching_contacts)

    def format_contacts(self, contacts):
        return [self._SourceResult(contact) for contact in contacts]

    def _new_search_engine(self, searched_columns, first_match_columns):
        return database.PersonalContactSearchEngine(
            Session, searched_columns, first_match_columns
        )

    @staticmethod
    def _remove_empty_values(dict_):
        return {attribute: value for attribute, value in dict_.items() if value}
