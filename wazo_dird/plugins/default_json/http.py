# Copyright 2016-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from time import time

from flask import request
from flask_restful import reqparse

from wazo_dird import auth
from wazo_dird.auth import required_acl
from wazo_dird.rest_api import AuthResource

logger = logging.getLogger(__name__)

parser = reqparse.RequestParser()
parser.add_argument('term', type=str, required=True, help='term is missing', location='args')

parser_reverse = reqparse.RequestParser()
parser_reverse.add_argument('exten', type=str, required=True, location='args')


def _error(code, msg):
    logger.error(msg)
    return {'reason': [msg],
            'timestamp': [time()],
            'status_code': code}, code


class DisabledFavoriteService:

    def favorite_ids(self, profile, xivo_user_uuid):
        return []


class Lookup(AuthResource):
    displays = None
    lookup_service = None
    favorite_service = DisabledFavoriteService()

    @classmethod
    def configure(cls, displays, lookup_service, favorite_service):
        cls.displays = displays
        cls.lookup_service = lookup_service
        if favorite_service:
            cls.favorite_service = favorite_service

    @required_acl('dird.directories.lookup.{profile}.read')
    def get(self, profile):
        args = parser.parse_args()
        term = args['term']

        logger.info('Lookup for %s with profile %s', term, profile)

        if profile not in self.displays:
            return _error(404, 'The profile `{profile}` does not exist'.format(profile=profile))

        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        xivo_user_uuid = token_infos['xivo_user_uuid']

        raw_results = self.lookup_service.lookup(term,
                                                 profile,
                                                 xivo_user_uuid,
                                                 token=token)
        favorites = self.favorite_service.favorite_ids(profile, xivo_user_uuid)
        formatter = _ResultFormatter(self.displays[profile])
        response = formatter.format_results(raw_results, favorites)

        response.update({'term': term})

        return response


class Reverse(AuthResource):
    reverse_service = None

    @classmethod
    def configure(cls, reverse_service):
        cls.reverse_service = reverse_service

    @required_acl('dird.directories.reverse.{profile}.{xivo_user_uuid}.read')
    def get(self, profile, xivo_user_uuid):
        token = request.headers['X-Auth-Token']
        args = parser_reverse.parse_args()
        exten = args['exten']

        logger.info('Reverse for %s with profile %s', exten, profile)

        # TODO check if profile exists

        raw_result = self.reverse_service.reverse(
            exten,
            profile,
            xivo_user_uuid=xivo_user_uuid,
            token=token)

        response = {'display': None,
                    'exten': exten,
                    'fields': {},
                    'source': None}

        if raw_result is not None:
            response['display'] = raw_result.fields.get('reverse')
            response['fields'] = raw_result.fields
            response['source'] = raw_result.source

        return response


class FavoritesRead(AuthResource):
    displays = None
    favorites_service = None

    @classmethod
    def configure(cls, displays, favorites_service):
        cls.displays = displays
        cls.favorites_service = favorites_service

    @required_acl('dird.directories.favorites.{profile}.read')
    def get(self, profile):
        logger.debug('Listing favorites with profile %s', profile)
        if profile not in self.displays:
            return _error(404, 'The profile `{profile}` does not exist'.format(profile=profile))

        token = request.headers.get('X-Auth-Token', '')
        token_infos = auth.client().token.get(token)

        try:
            raw_results = self.favorites_service.favorites(profile, token_infos['xivo_user_uuid'])
        except self.favorites_service.NoSuchProfileException as e:
            return _error(404, str(e))

        formatter = _FavoriteResultFormatter(self.displays[profile])
        return formatter.format_results(raw_results)


class FavoritesWrite(AuthResource):

    favorites_service = None

    @classmethod
    def configure(cls, favorites_service):
        cls.favorites_service = favorites_service

    @required_acl('dird.directories.favorites.{directory}.{contact}.update')
    def put(self, directory, contact):
        token = request.headers.get('X-Auth-Token', '')
        token_infos = auth.client().token.get(token)

        try:
            self.favorites_service.new_favorite(directory, contact, token_infos['xivo_user_uuid'])
        except self.favorites_service.DuplicatedFavoriteException:
            return _error(409, 'Adding this favorite would create a duplicate')
        except self.favorites_service.NoSuchSourceException as e:
            return _error(404, str(e))
        return '', 204

    @required_acl('dird.directories.favorites.{directory}.{contact}.delete')
    def delete(self, directory, contact):
        token = request.headers.get('X-Auth-Token', '')
        token_infos = auth.client().token.get(token)

        try:
            self.favorites_service.remove_favorite(
                directory,
                contact,
                token_infos['xivo_user_uuid'],
            )
            return '', 204
        except (self.favorites_service.NoSuchFavoriteException,
                self.favorites_service.NoSuchSourceException) as e:
            return _error(404, str(e))


class Personal(AuthResource):

    displays = None
    personal_service = None
    favorite_service = DisabledFavoriteService()

    @classmethod
    def configure(cls, displays, personal_service, favorite_service):
        cls.displays = displays
        cls.personal_service = personal_service
        if favorite_service:
            cls.favorite_service = favorite_service

    @required_acl('dird.directories.personal.{profile}.read')
    def get(self, profile):
        logger.debug('Listing personal with profile %s', profile)
        token = request.headers.get('X-Auth-Token', '')
        token_infos = auth.client().token.get(token)

        if profile not in self.displays:
            return _error(404, 'The profile `{profile}` does not exist'.format(profile=profile))

        raw_results = self.personal_service.list_contacts(token_infos)
        try:
            favorites = self.favorite_service.favorite_ids(profile, token_infos['xivo_user_uuid'])
        except self.favorite_service.NoSuchProfileException as e:
            return _error(404, str(e))
        formatter = _ResultFormatter(self.displays[profile])
        return formatter.format_results(raw_results, favorites)


class _ResultFormatter:

    def __init__(self, display):
        self._display = display
        self._headers = [d.title for d in display]
        self._types = [d.type for d in display]
        self._has_favorites = 'favorite' in self._types
        if self._has_favorites:
            self._favorite_field = [d.field for d in display if d.type == 'favorite'][0]
        self._personal_fields = [d.field for d in display if d.type == 'personal']

    def format_results(self, results, favorites):
        self._favorites = favorites
        return {
            'column_headers': self._headers,
            'column_types': self._types,
            'results': [self._format_result(r) for r in results]
        }

    def _format_result(self, result):
        if self._has_favorites:
            is_favorite = self._is_favorite(result)
            result.fields[self._favorite_field] = is_favorite

        result.fields.update(dict.fromkeys(self._personal_fields, result.is_personal))

        return {
            'column_values': [result.fields.get(d.field, d.default) for d in self._display],
            'relations': result.relations,
            'source': result.source,
        }

    def _is_favorite(self, result):
        if not self._has_favorites:
            return False

        if result.source not in self._favorites:
            return False

        source_entry_id = result.source_entry_id()
        if not source_entry_id:
            return False

        return source_entry_id in self._favorites[result.source]


class _FavoriteResultFormatter(_ResultFormatter):

    def format_results(self, results):
        return super().format_results(results, [])

    def _is_favorite(self, result):
        return True
