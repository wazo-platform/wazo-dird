# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import builtins
import logging
from collections.abc import Iterator
from typing import Any, cast

from requests import HTTPError
from unidecode import unidecode
from wazo_confd_client import Client as ConfdClient

from wazo_dird import BaseSourcePlugin, make_result_class
from wazo_dird.helpers import BackendViewDependencies, BaseBackendView
from wazo_dird.plugin_helpers.confd_client_registry import registry
from wazo_dird.plugins.base_plugins import SourcePluginDependencies
from wazo_dird.plugins.source_result import _SourceResult as SourceResult

from . import http

logger = logging.getLogger(__name__)


class ConferenceViewPlugin(BaseBackendView):
    backend = 'conference'
    list_resource = http.ConferenceList
    item_resource = http.ConferenceItem
    contact_list_resource = http.ConferenceContactList

    def load(self, dependencies: BackendViewDependencies) -> None:  # type: ignore[override]
        super().load(dependencies)
        api = dependencies['api']
        source_service = dependencies['services']['source']

        api.add_resource(
            self.contact_list_resource,
            '/backends/conference/sources/<source_uuid>/contacts',
            resource_class_args=(source_service,),
        )

    def unload(self) -> None:
        registry.unregister_all()


class ConferencePlugin(BaseSourcePlugin):
    _client: ConfdClient | None
    _searched_columns: builtins.list[str]
    _first_matched_columns: builtins.list[str]
    _SourceResult: type[SourceResult]

    def __init__(self) -> None:
        self._client = None
        self._uuid: str | None = None

    def load(self, dependencies: SourcePluginDependencies) -> None:
        config = dependencies['config']
        self._searched_columns = cast(
            'builtins.list[str]', config.get(self.SEARCHED_COLUMNS, [])
        )
        self._first_matched_columns = cast(
            'builtins.list[str]', config.get(self.FIRST_MATCHED_COLUMNS, [])
        )
        self.name = config['name']
        self._client = registry.get(config)

        self._SourceResult = make_result_class(
            'conference',
            self.name,
            'id',
            format_columns=cast(
                'dict[str, str] | None', config.get(self.FORMAT_COLUMNS)
            ),
        )
        logger.info('Wazo %s successfully loaded', config['name'])

    def unload(self) -> None:
        registry.unregister_all()

    def list(
        self, unique_ids: builtins.list[str], args: dict[str, Any] | None = None
    ) -> builtins.list[SourceResult]:
        logger.debug('Listing all conferences')
        contacts = self._fetch_contacts()
        matching_contacts = (c for c in contacts if str(c['id']) in unique_ids)
        results = [self._SourceResult(c) for c in matching_contacts]
        logger.debug('Found %s conferences', len(results))
        return results

    def search(  # type: ignore[override]
        self,
        term: str,
        profile: Any | None = None,
        args: dict[str, Any] | None = None,
    ) -> builtins.list[SourceResult]:
        logger.debug('Looking for all conferences matching "%s"', term)
        clean_term = unidecode(term.lower())
        contacts = self._fetch_contacts()
        matching_contacts = (c for c in contacts if self._search_filter(clean_term, c))
        results = [self._SourceResult(c) for c in matching_contacts]
        logger.debug('Found %s conferences', len(results))
        return results

    def first_match(
        self, term: str, args: dict[str, Any] | None = None
    ) -> SourceResult | None:
        logger.debug('Looking for first conference matching "%s"', term)
        lowered_term = term.lower()
        for contact in self._fetch_contacts():
            if self._first_match_filter(lowered_term, contact):
                logger.debug('Found one conference')
                return self._SourceResult(contact)
        logger.debug('Found no conference')
        return None

    def match_all(
        self, terms: builtins.list[str], args: dict[str, Any] | None = None
    ) -> dict[str, SourceResult]:
        logger.debug('Looking for conference matching "%s"', terms)
        results: dict[str, SourceResult] = {}
        for contact in self._fetch_contacts():
            for term in terms:
                lowered_term = term.lower()
                if self._first_match_filter(lowered_term, contact):
                    results[term] = self._SourceResult(contact)
                    logger.debug('Found one conference match to "%s"', term)

        if not results:
            logger.debug('Found no conference')
        return results

    def _first_match_filter(self, lowered_term: str, contact: dict[str, Any]) -> bool:
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

    def _search_filter(self, clean_term: str, contact: dict[str, Any]) -> bool:
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

    def _fetch_contacts(self) -> Iterator[dict[str, Any]]:
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
