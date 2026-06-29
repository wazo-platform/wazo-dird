# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import builtins
import logging
from typing import Any, cast

from wazo_dird import BaseSourcePlugin, make_result_class
from wazo_dird.helpers import AuthConfig, BackendViewDependencies, BaseBackendView
from wazo_dird.plugins.base_plugins import SourcePluginDependencies
from wazo_dird.plugins.source_result import _SourceResult as SourceResult

from . import services
from .exceptions import GoogleTokenNotFoundException
from .http import GoogleContactList, GoogleItem, GoogleList

logger = logging.getLogger(__name__)


class GoogleViewPlugin(BaseBackendView):
    backend = 'google'
    item_resource = GoogleItem
    list_resource = GoogleList
    contact_list_resource = GoogleContactList

    def load(self, dependencies: BackendViewDependencies) -> None:  # type: ignore[override]
        super().load(dependencies)
        api = dependencies['api']
        config = dependencies['config']
        auth_config = config['auth']
        source_service = dependencies['services']['source']
        args = (auth_config, config, source_service)

        api.add_resource(
            self.contact_list_resource,
            "/backends/google/sources/<source_uuid>/contacts",
            resource_class_args=args,
        )


class GooglePlugin(BaseSourcePlugin):
    auth: AuthConfig
    google: services.GoogleService
    unique_column: str
    _searched_columns: list[str]
    _first_matched_columns: list[str]
    _SourceResult: type[SourceResult]

    def load(self, dependencies: SourcePluginDependencies) -> None:
        config = dependencies['config']
        self.auth = cast('AuthConfig', dict(config)['auth'])
        self.name = config['name']
        self.google = services.GoogleService()
        self.unique_column = 'id'

        format_columns: dict[str, str] = dict(config.get('format_columns', {}))
        if 'reverse' not in format_columns:
            logger.info(
                'no "reverse" column has been configured on %s will use "name"',
                self.name,
            )
            format_columns['reverse'] = '{name}'

        self._SourceResult = make_result_class(
            'google', self.name, self.unique_column, format_columns
        )

        self._searched_columns = config.get('searched_columns', [])
        if not self._searched_columns:
            logger.info(
                'no "searched_columns" configured on "%s" no results will be matched',
                self.name,
            )

        self._first_matched_columns = config.get('first_matched_columns', [])
        if not self._first_matched_columns:
            logger.info(
                'no "first_matched_columns" configured on "%s" no results will be matched',
                self.name,
            )

    def search(
        self, term: str, args: dict[str, Any] | None = None
    ) -> list[SourceResult]:
        logger.debug('Searching term=%s', term)
        try:
            google_token = self._get_google_token(**(args or {}))
        except GoogleTokenNotFoundException:
            return []

        contacts = self.google.get_contacts_with_term(google_token, term)
        lowered_term = term.lower()
        filtered_contacts = [
            c for c in contacts if self._search_match_predicate(c, lowered_term)
        ]

        return [self._SourceResult(c) for c in filtered_contacts]

    def list(
        self, unique_ids: list[str], args: dict[str, Any] | None = None
    ) -> list[SourceResult]:
        try:
            google_token = self._get_google_token(**(args or {}))
        except GoogleTokenNotFoundException:
            return []

        contacts, _ = self.google.get_contacts(google_token)
        filtered_contacts = [c for c in contacts if c[self.unique_column] in unique_ids]

        return [self._SourceResult(contact) for contact in filtered_contacts]

    def first_match(
        self, term: str, args: dict[str, Any] | None = None
    ) -> SourceResult | None:
        if not self._first_matched_columns:
            logger.debug(
                '%s is a source for reverse lookups but does not have a "first_matched_columns"',
                self.name,
            )
            return None

        try:
            google_token = self._get_google_token(**(args or {}))
        except GoogleTokenNotFoundException:
            logger.debug('could not find a matching google token, aborting first_match')
            return None

        contacts, _ = self.google.get_contacts(google_token)
        lowered_term = term.lower()

        for contact in contacts:
            if self._first_match_predicate(lowered_term, contact):
                return self._SourceResult(contact)

    def match_all(
        self, terms: builtins.list[str], args: dict[str, Any] | None = None
    ) -> dict[str, SourceResult]:
        if not self._first_matched_columns:
            logger.debug(
                '%s is a source for reverse lookups but does not have a "first_matched_columns"',
                self.name,
            )
            return {}

        try:
            google_token = self._get_google_token(**(args or {}))
        except GoogleTokenNotFoundException:
            logger.debug('could not find a matching google token, aborting match_all')
            return {}

        contacts, _ = self.google.get_contacts(google_token)
        results: dict[str, SourceResult] = {}
        for term in terms:
            lowered_term = term.lower()
            for contact in contacts:
                if self._first_match_predicate(lowered_term, contact):
                    results[term] = self._SourceResult(contact)
        return results

    def _first_match_predicate(self, term: str, contact: dict[str, Any]) -> bool:
        for column in self._first_matched_columns:
            column_value = contact.get(column) or ''
            if isinstance(column_value, (dict, list)):
                for value in column_value:
                    if isinstance(value, dict):
                        for sub_value in value.values():
                            if term == sub_value.lower():
                                return True
                    else:
                        if term == value.lower():
                            return True
            else:
                if term == str(column_value).lower():
                    return True

        return False

    def _get_google_token(
        self, user_uuid: str, token: str | None = None, **ignored: Any
    ) -> str:
        if not token:
            logger.debug('Unable to search through Google without a token.')
            raise GoogleTokenNotFoundException(user_uuid)

        access_token = services.get_google_access_token(user_uuid, token, **self.auth)
        if access_token is None:
            raise GoogleTokenNotFoundException(user_uuid)
        return access_token

    def _search_match_predicate(self, contact: dict[str, Any], term: str) -> bool:
        for field in self._searched_columns:
            column_value = contact.get(field) or ''
            if isinstance(column_value, (dict, list)):
                for value in column_value:
                    if isinstance(value, dict):
                        for sub_value in value.values():
                            if term in sub_value.lower():
                                return True
                    else:
                        if term in value.lower():
                            return True
            else:
                if term in column_value.lower():
                    return True

        return False
