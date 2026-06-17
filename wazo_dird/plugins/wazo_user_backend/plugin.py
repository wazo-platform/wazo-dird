# Copyright 2014-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from typing import Any, cast

from requests.exceptions import ConnectionError, RequestException
from unidecode import unidecode
from wazo_confd_client import Client as ConfdClient

from wazo_dird import BaseSourcePlugin, make_result_class
from wazo_dird.helpers import BackendViewDependencies, BaseBackendView
from wazo_dird.plugin_helpers.confd_client_registry import registry
from wazo_dird.plugins.base_plugins import SourcePluginDependencies
from wazo_dird.plugins.source_result import _SourceResult as SourceResult

from . import http

logger = logging.getLogger(__name__)


class WazoUserView(BaseBackendView):
    backend = 'wazo'
    list_resource = http.WazoList
    item_resource = http.WazoItem
    contact_list_resource = http.WazoContactList

    def load(self, dependencies: BackendViewDependencies) -> None:  # type: ignore[override]
        super().load(dependencies)
        api = dependencies['api']
        source_service = dependencies['services']['source']

        api.add_resource(
            self.contact_list_resource,
            "/backends/wazo/sources/<source_uuid>/contacts",
            resource_class_args=((source_service,)),
        )

    def unload(self) -> None:
        registry.unregister_all()


class WazoUserPlugin(BaseSourcePlugin):
    _valid_keys = [
        'id',
        'exten',
        'firstname',
        'lastname',
        'userfield',
        'email',
        'description',
        'mobile_phone_number',
        'voicemail_number',
    ]
    _match_all_supported_columns = ['exten', 'mobile_phone_number']

    _client: ConfdClient | None
    _searched_columns: list[str]
    _first_matched_columns: list[str]
    _SourceResult: type[SourceResult]

    def __init__(self) -> None:
        self._client = None
        self._uuid: str | None = None
        self._search_params: dict[str, Any] = {'view': 'directory', 'recurse': True}

    def load(self, dependencies: SourcePluginDependencies) -> None:
        config = dependencies['config']
        self._searched_columns = config.get('searched_columns', [])
        self._first_matched_columns = config.get('first_matched_columns', [])
        self.name = config['name']
        self._client = registry.get(dict(config))

        self._SourceResult = make_result_class(
            'wazo', self.name, 'id', format_columns=config.get('format_columns')
        )
        self._search_params.update(
            cast('dict[str, Any]', config.get('extra_search_params', {}))
        )
        logger.info('Wazo %s successfully loaded', config['name'])

    def unload(self) -> None:
        registry.unregister_all()

    def search(  # type: ignore[override]
        self,
        term: str,
        profile: Any | None = None,
        args: dict[str, Any] | None = None,
    ) -> list[SourceResult]:
        clean_term = unidecode(term.lower())
        entries = self._fetch_entries(term)

        def match_fn(entry: SourceResult) -> bool:
            for column in self._searched_columns:
                column_value = entry.fields.get(column) or ''
                clean_column_value = unidecode(str(column_value).lower())
                logger.debug(
                    'entry\'s cleaned value for search column %s: %r',
                    column,
                    clean_column_value,
                )

                if clean_term in clean_column_value:
                    return True
            return False

        return [entry for entry in entries if match_fn(entry)]

    def first_match(
        self, term: str, args: dict[str, Any] | None = None
    ) -> SourceResult | None:
        logger.debug('Looking for "%s"', term)
        entries = self._fetch_entries(term)

        def match_fn(entry: SourceResult) -> bool:
            for column in self._first_matched_columns:
                if term == entry.fields.get(column):
                    return True
            return False

        for entry in entries:
            if match_fn(entry):
                logger.debug('Found a match: %s', entry)
                return entry
        logger.debug('Found no match')
        return None

    def match_all(
        self, terms: list[str], args: dict[str, Any] | None = None
    ) -> dict[str, SourceResult]:
        results: dict[str, SourceResult] = {}

        # NOTE(fblackburn) fallback if one of fields are not supported
        supported = all(
            column in self._match_all_supported_columns
            for column in self._first_matched_columns
        )
        first_match_faster = len(terms) < len(self._first_matched_columns)
        if not supported or first_match_faster:
            results = {}
            for term in terms:
                match = self.first_match(term, args=args)
                if match is not None:
                    results[term] = match
            return results

        for column in self._first_matched_columns:
            terms_merged = ','.join(terms)
            logger.debug('Looking for "%s"="%s"', column, terms)
            entries = self._fetch_entries(terms_merged, column)
            for entry in entries:
                value = entry.fields.get(column)
                if value is not None and value in terms:
                    results[value] = entry
                    logger.debug('Found a match: %s', entry)

        if not results:
            logger.debug('Found no match')
        return results

    def list(
        self, unique_ids: list[str], args: dict[str, Any] | None = None
    ) -> list[SourceResult]:
        entries = self._fetch_entries()

        def match_fn(entry: SourceResult) -> bool:
            for unique_id in unique_ids:
                if unique_id == entry.get_unique():
                    return True
            return False

        return [entry for entry in entries if match_fn(entry)]

    def _fetch_entries(
        self, term: str | None = None, column: str = 'search'
    ) -> Iterable[SourceResult]:
        try:
            uuid = self._get_uuid()
        except ConnectionError as e:
            logger.info('%s', e)
            return []
        except RequestException as e:
            response = getattr(e, 'response', None)
            status_code = getattr(response, 'status_code', None)
            logger.info(
                'Cannot fetch UUID status_code "%s". No results will be returned',
                status_code,
            )
            return []

        try:
            entries = self._fetch_users(term, column)
        except ConnectionError as e:
            logger.info('%s', e)
            return []
        except RequestException as e:
            response = getattr(e, 'response', None)
            status_code = getattr(response, 'status_code', None)

            logger.info(
                'Cannot fetch entries status_code "%s". No results will be returned',
                status_code,
            )
            return []

        return (self._source_result_from_entry(entry, uuid) for entry in entries)

    def _get_uuid(self) -> str:
        if self._uuid:
            return self._uuid

        assert self._client is not None
        infos = self._client.infos()
        uuid: str = infos['uuid']
        self._uuid = uuid
        return uuid

    def _fetch_users(
        self, term: str | None = None, column: str = 'search'
    ) -> Iterator[dict[str, Any]]:
        search_params = dict(self._search_params)
        if term:
            search_params[column] = term
        assert self._client is not None
        users = self._client.users.list(**search_params)
        logger.debug('Fetched %s users', users['total'])
        return (user for user in users['items'])

    def _source_result_from_entry(
        self, entry: dict[str, Any], uuid: str
    ) -> SourceResult:
        fields = {key: entry.get(key) for key in self._valid_keys}
        firstname = fields['firstname'] or ''
        lastname = fields['lastname'] or ''
        fullname = ' '.join(fragment for fragment in (firstname, lastname) if fragment)
        fields['full_name'] = fullname
        return self._SourceResult(
            fields,
            xivo_id=uuid,
            agent_id=entry['agent_id'],
            user_id=entry['id'],
            user_uuid=entry['uuid'],
            endpoint_id=entry['line_id'],
        )
