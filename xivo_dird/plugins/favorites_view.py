# -*- coding: utf-8 -*-
# Copyright (C) 2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import logging

from collections import namedtuple
from flask_restplus import Resource
from time import time
from xivo_dird import BaseViewPlugin
from xivo_dird.core.rest_api import api

logger = logging.getLogger(__name__)

DisplayColumn = namedtuple('DisplayColumn', ['title', 'type', 'default', 'field'])

parser = api.parser()
parser.add_argument('source', type=unicode, required=True, help='source is missing')
parser.add_argument('contact_id', type=list, required=True, help='contact_id is missing')


class FavoritesViewPlugin(BaseViewPlugin):

    def load(self, args=None):
        config = args['config']

        if 'favorites' not in args['services']:
            logger.error('Missing service plugin: favorites')
            return

        FavoritesView.configure(displays=make_displays(config),
                                favorites_service=args['services']['favorites'])


@api.route('/directories/favorites/<profile>')
class FavoritesView(Resource):
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

        raw_results = self.favorites_service(profile)
        return format_results(raw_results, display)

    def post(self, profile):
        args = parser.parse_args()
        logger.debug(repr(args['contact_id']))
        self.favorites_service.new_favorite(args['source'], tuple(args['contact_id']))
        return '', 201

    def delete(self, profile):
        args = parser.parse_args()
        self.favorites_service.remove_favorite(args['source'], tuple(args['contact_id']))
        return '', 204


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
    for profile, display_name in view_config['profile_to_display'].iteritems():
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
