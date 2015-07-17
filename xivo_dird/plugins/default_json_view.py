# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import logging

from collections import namedtuple
from flask import request
from flask_restful import reqparse
from time import time

from xivo_dird import BaseViewPlugin
from xivo_dird.core import auth
from xivo_dird.core.auth import AuthResource
from xivo_dird.core.rest_api import api

logger = logging.getLogger(__name__)

parser = reqparse.RequestParser()
parser.add_argument('term', type=unicode, required=True, help='term is missing', location='args')


class JsonViewPlugin(BaseViewPlugin):

    lookup_url = '/directories/lookup/<profile>'
    favorites_read_url = '/directories/favorites/<profile>'
    favorites_write_url = '/directories/favorites/<directory>/<contact>'

    def load(self, args=None):
        config = args['config']
        displays = make_displays(config)

        favorite_service = args['services'].get('favorites')
        lookup_service = args['services'].get('lookup')

        if lookup_service:
            Lookup.configure(displays=displays,
                             lookup_service=lookup_service,
                             favorite_service=favorite_service)

            api.add_resource(Lookup, self.lookup_url)
        else:
            logger.error('%s disabled: no service plugin `lookup`', self.lookup_url)

        if favorite_service:
            FavoritesRead.configure(displays=displays,
                                    favorites_service=favorite_service)
            FavoritesWrite.configure(favorites_service=favorite_service)

            api.add_resource(FavoritesRead, '/directories/favorites/<profile>')
            api.add_resource(FavoritesWrite, '/directories/favorites/<directory>/<contact>')
        else:
            logger.error('%s disabled: no service plugin `favorites`', self.favorites_read_url)
            logger.error('%s disabled: no service plugin `favorites`', self.favorites_write_url)


class Lookup(AuthResource):
    class DisabledFavoriteService(object):
        def favorite_ids(self, profile, token_info):
            return []

    displays = None
    lookup_service = None
    favorite_service = DisabledFavoriteService()

    @classmethod
    def configure(cls, displays, lookup_service, favorite_service):
        cls.displays = displays
        cls.lookup_service = lookup_service
        if favorite_service:
            cls.favorite_service = favorite_service

    def get(self, profile):
        args = parser.parse_args()
        term = args['term']

        logger.info('Lookup for %s with profile %s', term, profile)

        if profile not in self.displays:
            error = {
                'reason': ['The profile does not exist'],
                'timestamp': [time()],
                'status_code': 404,
            }
            return error, 404

        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)

        raw_results = self.lookup_service(term, profile, args={}, token_infos=token_infos)
        favorites = self.favorite_service.favorite_ids(profile, token_infos)

        formatter = _ResultFormatter(self.displays[profile])
        response = formatter.format_results(raw_results, favorites)

        response.update({'term': term})
        return response


class FavoritesRead(AuthResource):
    displays = None
    favorites_service = None

    @classmethod
    def configure(cls, displays, favorites_service):
        cls.displays = displays
        cls.favorites_service = favorites_service

    def get(self, profile):
        logger.debug('Listing favorites with profile %s', profile)
        if profile not in self.displays:
            error = {
                'reason': ['The profile does not exist'],
                'timestamp': [time()],
                'status_code': 404,
            }
            return error, 404

        token = request.headers.get('X-Auth-Token', '')
        token_infos = auth.client().token.get(token)

        raw_results = self.favorites_service.favorites(profile, token_infos)
        formatter = _FavoriteResultFormatter(self.displays[profile])
        return formatter.format_results(raw_results)


class FavoritesWrite(AuthResource):

    favorites_service = None

    @classmethod
    def configure(cls, favorites_service):
        cls.favorites_service = favorites_service

    def put(self, directory, contact):
        token = request.headers.get('X-Auth-Token', '')
        token_infos = auth.client().token.get(token)

        self.favorites_service.new_favorite(directory, contact, token_infos)
        return '', 204

    def delete(self, directory, contact):
        token = request.headers.get('X-Auth-Token', '')
        token_infos = auth.client().token.get(token)

        try:
            self.favorites_service.remove_favorite(directory, contact, token_infos)
            return '', 204
        except self.favorites_service.NoSuchFavorite as e:
            error = {
                'reason': [str(e)],
                'timestamp': [time()],
                'status_code': 404,
            }
            return error, 404


class _ResultFormatter(object):

    def __init__(self, display):
        self._display = display
        self._headers = [d.title for d in display]
        self._types = [d.type for d in display]
        self._has_favorites = 'favorite' in self._types
        if self._has_favorites:
            self._favorite_field = [d.field for d in display if d.type == 'favorite'][0]

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
        return super(_FavoriteResultFormatter, self).format_results(results, [])

    def _is_favorite(self, result):
        return True


def make_displays(view_config):
    result = {}
    for profile, display_name in view_config.get('profile_to_display', {}).iteritems():
        result[profile] = _make_display_from_name(view_config, display_name)
    return result


def _make_display_from_name(view_config, display_name):
    if display_name not in view_config['displays']:
        logger.warning('Display `%s` is not defined.', display_name)
    display = view_config['displays'].get(display_name, [])
    return [
        DisplayColumn(column.get('title'),
                      column.get('type'),
                      column.get('default'),
                      column.get('field'))
        for column in display
    ]

DisplayColumn = namedtuple('DisplayColumn', ['title', 'type', 'default', 'field'])
