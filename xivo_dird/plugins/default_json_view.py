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

    def load(self, args=None):
        config = args['config']
        displays = make_displays(config)

        lookup_url = '/directories/lookup/<profile>'
        if 'lookup' in args['services']:
            Lookup.configure(displays=displays,
                             lookup_service=args['services']['lookup'])

            api.add_resource(Lookup, lookup_url)
        else:
            logger.error('%s disabled: no service plugin `lookup`', lookup_url)

        favorites_read_url = '/directories/favorites/<profile>'
        favorites_write_url = '/directories/favorites/<directory>/<contact>'
        if 'favorites' in args['services']:
            FavoritesRead.configure(displays=displays,
                                    favorites_service=args['services']['favorites'])
            FavoritesWrite.configure(favorites_service=args['services']['favorites'])

            api.add_resource(FavoritesRead, '/directories/favorites/<profile>')
            api.add_resource(FavoritesWrite, '/directories/favorites/<directory>/<contact>')
        else:
            logger.error('%s disabled: no service plugin `favorites`', favorites_read_url)
            logger.error('%s disabled: no service plugin `favorites`', favorites_write_url)


class Lookup(AuthResource):
    displays = None
    lookup_service = None

    @classmethod
    def configure(cls, displays, lookup_service):
        cls.displays = displays
        cls.lookup_service = lookup_service

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

        raw_results = self.lookup_service(term, profile, args={})
        display = self.displays[profile]
        response = format_results(raw_results, display)

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

        display = self.displays[profile]

        token = request.headers.get('X-Auth-Token', '')
        token_infos = auth.client().token.get(token)

        raw_results = self.favorites_service.favorites(profile, token_infos)
        return format_results(raw_results, display)


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


def format_results(results, display):
    return {
        'column_headers': [d.title for d in display],
        'column_types': [d.type for d in display],
        'results': [_format_result(r, display) for r in results]
    }


def _format_result(result, display):
    return {
        'column_values': [result.fields.get(d.field, d.default) for d in display],
        'relations': result.relations,
        'source': result.source,
    }


def make_displays(view_config):
    result = {}
    for profile, display_name in view_config.get('profile_to_display', {}).iteritems():
        result[profile] = _make_display_from_name(view_config, display_name)
    return result


def _make_display_from_name(view_config, display_name):
    return [
        DisplayColumn(display.get('title'),
                      display.get('type'),
                      display.get('default'),
                      display.get('field'))
        for display in view_config['displays'][display_name]
    ]

DisplayColumn = namedtuple('DisplayColumn', ['title', 'type', 'default', 'field'])
