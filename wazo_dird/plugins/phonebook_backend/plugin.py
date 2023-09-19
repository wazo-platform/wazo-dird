# Copyright 2016-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import builtins
import logging
from typing import TypedDict

from wazo_dird import BaseSourcePlugin, database, make_result_class
from wazo_dird.database.helpers import Session
from wazo_dird.database.queries.phonebook import PhonebookCRUD
from wazo_dird.exception import InvalidConfigError, NoSuchPhonebook, NoSuchSource
from wazo_dird.helpers import (
    BackendViewDependencies,
    BackendViewServices,
    BaseBackendView,
)
from wazo_dird.plugins.base_plugins import SourceConfig as BaseSourceConfig
from wazo_dird.plugins.phonebook_service.plugin import _PhonebookService
from wazo_dird.plugins.source_result import _SourceResult as SourceResult
from wazo_dird.plugins.source_service.plugin import _SourceService
from xivo.pubsub import Pubsub
from . import http

logger = logging.getLogger(__name__)


class Services(BackendViewServices):
    phonebook: _PhonebookService


class PhonebookViewDependencies(BackendViewDependencies):
    services: Services  # type: ignore[misc]


class PhonebookView(BaseBackendView):
    backend = 'phonebook'
    list_resource = http.PhonebookList
    item_resource = http.PhonebookItem
    contact_resource = http.PhonebookContactList

    def load(self, dependencies: PhonebookViewDependencies):  # type: ignore[override]
        super().load(dependencies)  # type: ignore[arg-type]
        api = dependencies['api']
        source_service = dependencies['services']['source']
        phonebook_service = dependencies['services']['phonebook']
        pubsub: Pubsub = dependencies['internal_pubsub']
        args = (source_service, phonebook_service)

        api.add_resource(
            self.contact_resource,
            f'/backends/{self.backend}/sources/<source_uuid>/contacts',
            resource_class_args=args,
        )

        def on_phonebook_delete_cascade(phonebook_uuid: str):
            sources = source_service.list_(
                backend='phonebook',
                visible_tenants=None,
                extra_fields={'phonebook_uuid': phonebook_uuid},
            )
            for source in sources:
                logger.info(
                    'phonebook %s deleted, deleting associated source %s',
                    phonebook_uuid,
                    source['uuid'],
                )
                try:
                    source_service.delete(
                        backend='phonebook',
                        source_uuid=source['uuid'],
                        visible_tenants=None,
                    )
                except NoSuchSource:
                    logger.info('source %s already deleted', source['uuid'])

        pubsub.subscribe('phonebook.deleted', on_phonebook_delete_cascade)

    def _get_view_args(self, dependencies: BackendViewDependencies):
        config = dependencies['config']
        source_service = dependencies['services']['source']
        phonebook_dao = PhonebookCRUD(Session)
        return (self.backend, source_service, config['auth'], phonebook_dao)


class Config(BaseSourceConfig, total=False):
    phonebook_uuid: str


class Dependencies(TypedDict):
    config: Config


class PhonebookPlugin(BaseSourcePlugin):
    _crud: database.PhonebookCRUD
    _source_name: str
    _search_engine: database.PhonebookContactSearchEngine
    _SourceResult: type[SourceResult]
    _source_service: _SourceService

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
        format_columns = config.get('format_columns', {})
        searched_columns = config.get('searched_columns')
        first_matched_columns = config.get('first_matched_columns')

        self._crud = database.PhonebookCRUD(Session)
        self._source_service: _SourceService = dependencies['services']['source']

        tenant_uuid = config['tenant_uuid']
        phonebook_key = self._get_phonebook_key(tenant_uuid, config)

        try:
            phonebook = self._crud.get(
                visible_tenants=[tenant_uuid], phonebook_key=phonebook_key
            )
        except NoSuchPhonebook:
            logger.info(
                'Phonebook source plugin loaded but phonebook missing(source_uuid=%s, phonebook_uuid=%s). Cleaning up obsolete source.',
                config['uuid'],
                config['phonebook_uuid'],
            )
        else:
            logger.debug(
                'Found phonebook (uuid=%s, name=%s) for source (source_uuid=%s, name=%s)',
                phonebook['uuid'],
                phonebook['name'],
                config['uuid'],
                config['name'],
            )

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

    def search(self, term: str, args=None) -> list[SourceResult]:
        logger.debug('Searching phonebook contact with %s', term)
        matching_contacts = self._search_engine.find_contacts(term)
        return self.format_contacts(matching_contacts)

    def first_match(self, exten: str, args=None) -> SourceResult | None:
        logger.debug('First matching phonebook contacts with %s', exten)
        matching_contact = self._search_engine.find_first_contact(exten)
        if not matching_contact:
            logger.debug('Found no matching contact.')
            return None

        for contact in self.format_contacts([matching_contact]):
            logger.debug('Found one matching contact.')
            return contact
        else:
            return None

    def list(self, source_entry_ids: list[str], args=None) -> list[SourceResult]:
        logger.debug('Listing phonebook contacts')
        matching_contacts = self._search_engine.list_contacts(source_entry_ids)
        return self.format_contacts(matching_contacts)

    def format_contacts(self, contacts) -> builtins.list[SourceResult]:
        return [self._SourceResult(c) for c in contacts]

    def _get_phonebook_key(
        self, tenant_uuid: str, config: Config
    ) -> database.PhonebookKey:
        if 'phonebook_uuid' in config:
            return database.PhonebookKey(uuid=config['phonebook_uuid'])
        else:
            phonebook_name = config['name']
            phonebooks = self._crud.list([tenant_uuid], search=phonebook_name)
            for phonebook in phonebooks:
                if phonebook['name'] == phonebook_name:
                    return database.PhonebookKey(uuid=phonebook['uuid'])

            raise InvalidConfigError(
                f'sources/{self._source_name}/phonebook_name',
                f'unknown phonebook {phonebook_name}',
            )
