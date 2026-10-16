# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import builtins
import logging
from collections.abc import Iterator, Mapping
from typing import Any, cast

from wazo_dird import BaseSourcePlugin, make_result_class
from wazo_dird.helpers import AuthConfig, BackendViewDependencies, BaseBackendView
from wazo_dird.plugins.base_plugins import LookupArgs, SourcePluginDependencies
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
        self.google = services.GoogleService(
            services.shared_contacts_cache(dependencies['main_config'])
        )
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

    def search(self, term: str, args: LookupArgs | None = None) -> list[SourceResult]:
        logger.debug('Searching term=%s', term)
        token_args: Mapping[str, Any] = args or {}
        try:
            google_token = self._get_google_token(**token_args)
        except GoogleTokenNotFoundException:
            return []

        contacts = self.google.search(google_token, term, self._searched_columns)
        return [self._SourceResult(c) for c in contacts]

    def list(
        self, unique_ids: list[str], args: dict[str, Any] | None = None
    ) -> list[SourceResult]:
        try:
            google_token = self._get_google_token(**(args or {}))
        except GoogleTokenNotFoundException:
            return []

        contacts = self.google.get_all_contacts(google_token)
        wanted_ids = set(unique_ids)
        filtered_contacts = [c for c in contacts if c[self.unique_column] in wanted_ids]

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

        contacts = self.google.get_all_contacts(google_token)
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

        contacts = self.google.get_all_contacts(google_token)
        terms_by_lowered: dict[str, builtins.list[str]] = {}
        for term in terms:
            terms_by_lowered.setdefault(term.lower(), []).append(term)

        # One pass over the contacts for all the terms; like first_match run
        # per term, except that the last matching contact wins
        results: dict[str, SourceResult] = {}
        for contact in contacts:
            for text in self._first_matched_texts(contact):
                for term in terms_by_lowered.get(text.lower(), []):
                    results[term] = self._SourceResult(contact)
        return results

    def _first_match_predicate(self, term: str, contact: dict[str, Any]) -> bool:
        return any(term == text.lower() for text in self._first_matched_texts(contact))

    def _first_matched_texts(self, contact: dict[str, Any]) -> Iterator[str]:
        for column in self._first_matched_columns:
            yield from services.column_texts(contact.get(column))

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
