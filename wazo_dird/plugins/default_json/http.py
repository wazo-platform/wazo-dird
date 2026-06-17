# Copyright 2016-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from time import time
from typing import TYPE_CHECKING, Any, cast

from flask import request
from flask_restful import reqparse
from requests.exceptions import HTTPError
from xivo.tenant_flask_helpers import Tenant

from wazo_dird import auth
from wazo_dird.auth import required_acl
from wazo_dird.exception import (
    NoSuchProfile,
    NoSuchProfileAPIException,
    NoSuchUser,
    OldAPIException,
)
from wazo_dird.helpers import DisplayAwareResource, DisplayColumn, ProfileConfig
from wazo_dird.http import AuthResource, LegacyAuthResource
from wazo_dird.plugins.source_result import _SourceResult as SourceResult

if TYPE_CHECKING:
    from wazo_auth_client import Client as AuthClient

    from wazo_dird.plugins.display_service.plugin import _DisplayService
    from wazo_dird.plugins.favorites_service.plugin import _FavoritesService
    from wazo_dird.plugins.lookup_service.plugin import _LookupService
    from wazo_dird.plugins.personal_service.plugin import _PersonalService
    from wazo_dird.plugins.profile_service.plugin import _ProfileService
    from wazo_dird.plugins.reverse_service.plugin import _ReverseService

logger = logging.getLogger(__name__)

parser = reqparse.RequestParser()
parser.add_argument(
    'term', type=str, required=True, help='term is missing', location='args'
)

parser_reverse = reqparse.RequestParser()
parser_reverse.add_argument('exten', type=str, required=True, location='args')


def _error(code: int, msg: str) -> tuple[dict[str, Any], int]:
    logger.error(msg)
    return {'reason': [msg], 'timestamp': [time()], 'status_code': code}, code


class DisabledFavoriteService:
    def favorite_ids(self, profile: dict[str, Any], user_uuid: str) -> list[Any]:
        return []


class Lookup(LegacyAuthResource, DisplayAwareResource):
    def __init__(
        self,
        lookup_service: _LookupService,
        favorite_service: _FavoritesService,
        display_service: _DisplayService,
        profile_service: _ProfileService,
    ) -> None:
        self.lookup_service = lookup_service
        self.favorite_service = favorite_service
        self.display_service = display_service
        self.profile_service = profile_service

    @required_acl('dird.directories.lookup.{profile}.read')
    def get(self, profile: str) -> dict[str, Any] | tuple[dict[str, Any], int]:
        args = parser.parse_args()
        term = args['term']

        logger.info('Lookup for %s with profile %s', term, profile)

        tenant = Tenant.autodetect()
        try:
            profile_config = self.profile_service.get_by_name(tenant.uuid, profile)
            display = self.build_display(profile_config)
        except OldAPIException as e:
            return e.body, e.status_code

        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        user_uuid = token_infos['metadata']['uuid']

        raw_results = self.lookup_service.lookup(
            cast(ProfileConfig, profile_config),
            tenant.uuid,
            term,
            user_uuid,
            token=token,
        )
        favorites = self.favorite_service.favorite_ids(
            cast(ProfileConfig, profile_config), user_uuid
        ).by_name
        formatter = _ResultFormatter(display)
        response = formatter.format_results(raw_results, favorites)

        response.update({'term': term})

        return response


class LookupByUUID(AuthResource, DisplayAwareResource):
    def __init__(
        self,
        lookup_service: _LookupService,
        favorite_service: _FavoritesService,
        display_service: _DisplayService,
        profile_service: _ProfileService,
        auth_client: AuthClient,
    ) -> None:
        self.lookup_service = lookup_service
        self.favorite_service = favorite_service
        self.display_service = display_service
        self.profile_service = profile_service
        self.auth_client = auth_client

    @required_acl('dird.directories.lookup.{profile}.{user_uuid}.read')
    def get(self, profile: str, user_uuid: str) -> dict[str, Any]:
        args = parser.parse_args()
        term = args['term']

        logger.info('Lookup %s for user %s with profile %s', term, user_uuid, profile)

        tenant_uuid = Tenant.autodetect().uuid
        try:
            profile_config = self.profile_service.get_by_name(tenant_uuid, profile)
            display = self.build_display(profile_config)
        except NoSuchProfile as e:
            raise NoSuchProfileAPIException(e.profile)

        token = request.headers['X-Auth-Token']

        raw_results = self.lookup_service.lookup(
            cast(ProfileConfig, profile_config),
            tenant_uuid,
            term,
            user_uuid,
            token=token,
        )
        favorites = self.favorite_service.favorite_ids(
            cast(ProfileConfig, profile_config), user_uuid
        ).by_name
        formatter = _ResultFormatter(display)
        response = formatter.format_results(raw_results, favorites)

        response.update({'term': term})

        return response

    def _get_user_tenant_uuid(self, user_uuid: str) -> str:
        try:
            tenant_uuid: str = self.auth_client.users.get(user_uuid)['tenant_uuid']
            return tenant_uuid
        except HTTPError as e:
            response = getattr(e, 'response', None)
            status_code = getattr(response, 'status_code', None)
            if status_code == 404:
                raise NoSuchUser(user_uuid)
            raise


class Reverse(LegacyAuthResource):
    def __init__(
        self, reverse_service: _ReverseService, profile_service: _ProfileService
    ) -> None:
        self.reverse_service = reverse_service
        self.profile_service = profile_service

    @required_acl('dird.directories.reverse.{profile}.{user_uuid}.read')
    def get(
        self, profile: str, user_uuid: str
    ) -> dict[str, Any] | tuple[dict[str, Any], int]:
        token = request.headers['X-Auth-Token']
        args = parser_reverse.parse_args()
        exten = args['exten']

        tenant = Tenant.autodetect()
        try:
            profile_config = self.profile_service.get_by_name(tenant.uuid, profile)
        except OldAPIException as e:
            return e.body, e.status_code

        logger.info('Reverse for %s with profile %s', exten, profile)

        raw_result = self.reverse_service.reverse(
            cast(ProfileConfig, profile_config),
            exten,
            profile,
            user_uuid=user_uuid,
            token=token,
        )

        response: dict[str, Any] = {
            'display': None,
            'exten': exten,
            'fields': {},
            'source': None,
        }

        if raw_result is not None:
            response['display'] = raw_result.fields.get('reverse')
            response['fields'] = raw_result.fields
            response['source'] = raw_result.source

        return response


class FavoritesRead(LegacyAuthResource, DisplayAwareResource):
    def __init__(
        self,
        favorites_service: _FavoritesService,
        display_service: _DisplayService,
        profile_service: _ProfileService,
    ) -> None:
        self.favorites_service = favorites_service
        self.display_service = display_service
        self.profile_service = profile_service

    @required_acl('dird.directories.favorites.{profile}.read')
    def get(self, profile: str) -> dict[str, Any] | tuple[dict[str, Any], int]:
        logger.debug('Listing favorites with profile %s', profile)
        tenant = Tenant.autodetect()
        try:
            profile_config = self.profile_service.get_by_name(tenant.uuid, profile)
            display = self.build_display(profile_config)
        except OldAPIException as e:
            return e.body, e.status_code

        token = request.headers.get('X-Auth-Token', '')
        token_infos = auth.client().token.get(token)

        try:
            raw_results = self.favorites_service.favorites(
                cast(ProfileConfig, profile_config),
                token_infos['metadata']['uuid'],
                token,
            )
        except self.favorites_service.NoSuchProfileException as e:
            return _error(404, str(e))

        formatter = _FavoriteResultFormatter(display)
        return formatter.format_results(raw_results)


class FavoritesWrite(LegacyAuthResource):
    def __init__(self, favorites_service: _FavoritesService) -> None:
        self.favorites_service = favorites_service

    @required_acl('dird.directories.favorites.{directory}.{contact}.update')
    def put(
        self, directory: str, contact: str
    ) -> tuple[str, int] | tuple[dict[str, Any], int]:
        token = request.headers.get('X-Auth-Token', '')
        token_infos = auth.client().token.get(token)

        tenant = Tenant.autodetect()
        try:
            self.favorites_service.new_favorite(
                tenant.uuid, directory, contact, token_infos['metadata']['uuid']
            )
        except self.favorites_service.DuplicatedFavoriteException:
            return _error(409, 'Adding this favorite would create a duplicate')
        except self.favorites_service.NoSuchSourceException as e:
            return _error(404, str(e))
        return '', 204

    @required_acl('dird.directories.favorites.{directory}.{contact}.delete')
    def delete(
        self, directory: str, contact: str
    ) -> tuple[str, int] | tuple[dict[str, Any], int]:
        token = request.headers.get('X-Auth-Token', '')
        token_infos = auth.client().token.get(token)

        tenant = Tenant.autodetect()
        try:
            self.favorites_service.remove_favorite(
                tenant.uuid, directory, contact, token_infos['metadata']['uuid']
            )
            return '', 204
        except (
            self.favorites_service.NoSuchFavoriteException,
            self.favorites_service.NoSuchSourceException,
        ) as e:
            return _error(404, str(e))


class Personal(LegacyAuthResource, DisplayAwareResource):
    def __init__(
        self,
        personal_service: _PersonalService,
        favorite_service: _FavoritesService | None,
        display_service: _DisplayService,
        profile_service: _ProfileService,
    ) -> None:
        self.personal_service = personal_service
        # DisabledFavoriteService is a null-object stand-in for the favorites
        # service used when no favorites service plugin is loaded.
        self.favorite_service: _FavoritesService = favorite_service or cast(
            '_FavoritesService', DisabledFavoriteService()
        )
        self.display_service = display_service
        self.profile_service = profile_service

    @required_acl('dird.directories.personal.{profile}.read')
    def get(self, profile: str) -> dict[str, Any] | tuple[dict[str, Any], int]:
        logger.debug('Listing personal with profile %s', profile)
        token = request.headers.get('X-Auth-Token', '')
        token_infos = auth.client().token.get(token)

        tenant = Tenant.autodetect()
        try:
            profile_config = self.profile_service.get_by_name(tenant.uuid, profile)
            display = self.build_display(profile_config)
        except OldAPIException as e:
            return e.body, e.status_code

        raw_results = self.personal_service.list_contacts(
            tenant.uuid, token_infos['metadata']['uuid']
        )

        try:
            favorites = self.favorite_service.favorite_ids(
                cast(ProfileConfig, profile_config), token_infos['metadata']['uuid']
            ).by_name
        except self.favorite_service.NoSuchProfileException as e:
            return _error(404, str(e))
        formatter = _ResultFormatter(display)
        return formatter.format_results(raw_results, favorites)


class _ResultFormatter:
    def __init__(self, display: list[DisplayColumn] | None) -> None:
        self._display: list[DisplayColumn] = display or []
        self._headers = [d.title for d in self._display]
        self._types = [d.type for d in self._display]
        self._has_favorites = 'favorite' in self._types
        if self._has_favorites:
            self._favorite_field = [
                d.field for d in self._display if d.type == 'favorite'
            ][0]
        self._personal_fields = [d.field for d in self._display if d.type == 'personal']
        self._favorites: dict[str, Any] = {}

    def format_results(
        self, results: list[SourceResult], favorites: dict[str, Any]
    ) -> dict[str, Any]:
        self._favorites = favorites
        return {
            'column_headers': self._headers,
            'column_types': self._types,
            'results': [self._format_result(r) for r in results],
        }

    def _format_result(self, result: SourceResult) -> dict[str, Any]:
        if self._has_favorites:
            is_favorite = self._is_favorite(result)
            result.fields[self._favorite_field] = is_favorite

        result.fields.update(
            dict.fromkeys(self._personal_fields, getattr(result, 'is_personal', False))
        )

        return {
            'column_values': [
                result.fields.get(d.field, d.default) for d in self._display
            ],
            'relations': result.relations,
            'source': result.source,
            'backend': result.backend,
        }

    def _is_favorite(self, result: SourceResult) -> bool:
        if not self._has_favorites:
            return False

        if result.source not in self._favorites:
            return False

        source_entry_id = result.source_entry_id()
        if not source_entry_id:
            return False

        return source_entry_id in self._favorites[result.source]


class _FavoriteResultFormatter(_ResultFormatter):
    def format_results(
        self, results: list[SourceResult], favorites: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return super().format_results(results, {})

    def _is_favorite(self, result: SourceResult) -> bool:
        return True
