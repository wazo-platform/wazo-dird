# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import builtins
import logging
from collections.abc import Callable, Mapping
from typing import Any

from wazo_dird import BaseSourcePlugin, database, make_result_class
from wazo_dird.database.helpers import Session
from wazo_dird.database.queries.base import ContactInfo
from wazo_dird.database.queries.personal import PersonalContactSearchEngine
from wazo_dird.helpers import BaseBackendView
from wazo_dird.plugins.base_plugins import SourcePluginDependencies
from wazo_dird.plugins.source_result import _SourceResult as SourceResult

from . import http

logger = logging.getLogger(__name__)


class PersonalView(BaseBackendView):
    backend = 'personal'
    list_resource = http.PersonalList
    item_resource = http.PersonalItem


class PersonalBackend(BaseSourcePlugin):
    _SourceResult: Callable[[ContactInfo], SourceResult]
    _search_engine: PersonalContactSearchEngine

    def load(
        self,
        config: SourcePluginDependencies,
        search_engine: PersonalContactSearchEngine | None = None,
    ) -> None:
        logger.debug('Loading personal source')

        unique_column = 'id'
        source_config = config['config']
        source_name = source_config['name']
        format_columns = source_config.get('format_columns', {})

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
            source_config.get('searched_columns'),
            source_config.get('first_matched_columns'),
        )

    def search(
        self, term: str, args: dict[str, Any] | None = None
    ) -> builtins.list[SourceResult]:
        logger.debug('Searching personal contacts with %s', term)
        assert args is not None
        user_uuid = args['user_uuid']
        matching_contacts = self._search_engine.find_personal_contacts(user_uuid, term)
        return self.format_contacts(matching_contacts)

    def first_match(
        self, term: str, args: dict[str, Any] | None = None
    ) -> SourceResult | None:
        logger.debug('First matching personal contacts with %s', term)
        assert args is not None
        user_uuid = args['user_uuid']
        matching_contacts = self._search_engine.find_first_personal_contact(
            user_uuid, term
        )
        for contact in self.format_contacts(matching_contacts):
            return contact
        return None

    def list(
        self, source_entry_ids: builtins.list[str], args: dict[str, Any] | None
    ) -> builtins.list[SourceResult]:
        logger.debug('Listing personal contacts: %s', source_entry_ids)
        assert args is not None
        user_uuid = args['user_uuid']
        matching_contacts = self._search_engine.list_personal_contacts(
            user_uuid, source_entry_ids
        )
        return self.format_contacts(matching_contacts)

    def format_contacts(
        self, contacts: builtins.list[ContactInfo]
    ) -> builtins.list[SourceResult]:
        return [self._SourceResult(contact) for contact in contacts]

    def _new_search_engine(
        self,
        searched_columns: builtins.list[str] | None,
        first_match_columns: builtins.list[str] | None,
    ) -> PersonalContactSearchEngine:
        return database.PersonalContactSearchEngine(
            Session, searched_columns, first_match_columns
        )

    @staticmethod
    def _remove_empty_values(dict_: Mapping[str, Any]) -> dict[str, Any]:
        return {attribute: value for attribute, value in dict_.items() if value}
