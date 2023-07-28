# Copyright 2016-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import logging
from typing import TypedDict

from wazo_dird import BaseSourcePlugin, database, make_result_class
from wazo_dird.database.helpers import Session
from wazo_dird.exception import InvalidConfigError
from wazo_dird.helpers import BaseBackendView

from . import http

logger = logging.getLogger(__name__)


class PhonebookView(BaseBackendView):
    backend = 'phonebook'
    list_resource = http.PhonebookList
    item_resource = http.PhonebookItem


class _Config(TypedDict):
    name: str  # phonebook source name
    tenant_uuid: str


class Config(_Config, total=False):
    phonebook_uuid: str
    phonebook_id: int


class Dependencies(TypedDict):
    config: Config


class PhonebookPlugin(BaseSourcePlugin):
    _crud: database.PhonebookCRUD
    _source_name: str
    _search_engine: database.PhonebookContactSearchEngine

    def __init__(self) -> None:
        super().__init__()
        self._crud = None  # type: ignore[assignment]
        self._search_engine = None  # type: ignore[assignment]
        self._source_name = None  # type: ignore[assignment]

    def load(self, dependencies: Dependencies):
        logger.debug('Loading phonebook source')
        unique_column = 'id'
        config = dependencies['config']
        self._source_name = config['name']
        format_columns = config.get(self.FORMAT_COLUMNS, {})
        searched_columns = config.get(self.SEARCHED_COLUMNS)
        first_matched_columns = config.get(self.FIRST_MATCHED_COLUMNS)

        self._crud = database.PhonebookCRUD(Session)

        tenant_uuid = config['tenant_uuid']
        phonebook_key = self._get_phonebook_key(tenant_uuid, config)

        self._search_engine = database.PhonebookContactSearchEngine(
            Session,
            [tenant_uuid],
            phonebook_key,
            searched_columns,
            first_matched_columns,
        )

        self._SourceResult = make_result_class(
            'phonebook', self._source_name, unique_column, format_columns
        )

        logger.info('%s loaded', self._source_name)

    def search(self, term, *args, **kwargs):
        logger.debug('Searching phonebook contact with %s', term)
        matching_contacts = self._search_engine.find_contacts(term)
        return self.format_contacts(matching_contacts)

    def first_match(self, term, *args, **kwargs):
        logger.debug('First matching phonebook contacts with %s', term)
        matching_contact = self._search_engine.find_first_contact(term)
        if not matching_contact:
            logger.debug('Found no matching contact.')
            return None

        for contact in self.format_contacts([matching_contact]):
            logger.debug('Found one matching contact.')
            return contact

    def list(self, source_entry_ids, args=None):
        logger.debug('Listing phonebook contacts')
        matching_contacts = self._search_engine.list_contacts(source_entry_ids)
        return self.format_contacts(matching_contacts)

    def format_contacts(self, contacts):
        return [self._SourceResult(c) for c in contacts]

    def _wait_until_loaded(self):
        logger.debug('waiting until loaded')
        if self._is_loaded.wait(timeout=1.0) is not True:
            logger.error('%s is not initialized', self._source_name)

    def _get_phonebook_key(
        self, tenant_uuid: str, config: Config
    ) -> database.PhonebookKey:
        if 'phonebook_uuid' in config:
            return database.PhonebookKey(uuid=config['phonebook_uuid'])
        elif 'phonebook_id' in config:
            return database.PhonebookKey(id=config['phonebook_id'])

        phonebook_name = config['name']
        phonebooks = self._crud.list([tenant_uuid], search=phonebook_name)
        for phonebook in phonebooks:
            if phonebook['name'] == phonebook_name:
                return database.PhonebookKey(uuid=phonebook['uuid'])

        raise InvalidConfigError(
            f'sources/{self._source_name}/phonebook_name',
            f'unknown phonebook {phonebook_name}',
        )
