# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Avencall
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
from flask_restplus import Resource
from flask_restplus import fields
from time import time
from xivo_dird import BaseViewPlugin

logger = logging.getLogger(__name__)


DisplayColumn = namedtuple('DisplayColumn', ['title', 'type', 'default', 'field'])


class JsonViewPlugin(BaseViewPlugin):

    def load(self, args=None):
        if 'lookup' not in args['services']:
            logger.error('HTTP view loaded without a lookup service')
            return

        api = args['rest_api']
        config = args['config']
        namespace = args['http_namespace']

        lookup_service = args['services']['lookup']
        displays = self._get_display_dict(config)

        route = '/lookup/<profile>'
        doc = {
            'model': api.model('Lookup', {
                'column_headers': fields.List(fields.String, description='The labels of the result header'),
                'column_types': fields.List(fields.String, description='The types of the result header'),
                'results': fields.List(fields.List(fields.String), description='The values of the results'),
                'term': fields.String(description='The string to look for'),
            }),
            'params': {
                'term': {
                    'description': 'The string to look for',
                    'required': False,
                    'type': 'string',
                    'paramType': 'query',
                }
            },
            'responses': {
                404: 'Invalid profile'
            }
        }

        api_class = make_api_class(lookup_service, displays, api)
        namespace.route(route, doc=doc)(api_class)

    def _get_display_dict(self, view_config):
        result = {}
        for profile, display_name in view_config['profile_to_display'].iteritems():
            result[profile] = self._display_from_name(view_config, display_name)
        return result

    def _display_from_name(self, view_config, display_name):
        return [
            DisplayColumn(display.get('title'), display.get('type'),
                          display.get('default'), display.get('field'))
            for display in view_config['displays'][display_name]
        ]


def make_api_class(lookup_service, displays, api):

    parser = api.parser()
    parser.add_argument('term', type=unicode, required=True, help='term is missing', location='args')

    class Lookup(Resource):

        def get(self, profile):
            args = parser.parse_args()
            term = args['term']

            logger.info('Lookup for %s with profile %s', term, profile)
            if profile not in displays:
                error = {
                    'reason': ['The lookup profile does not exist'],
                    'timestamp': [time()],
                    'status_code': 404,
                }
                return error, 404

            display = displays[profile]

            return _lookup(lookup_service, display, term, profile)

    return Lookup


def _lookup(lookup_service, display, term, profile):
    raw_results = lookup_service(term, profile, args={})
    return {
        'term': term,
        'column_headers': [d.title for d in display],
        'column_types': [d.type for d in display],
        'results': [DisplayAwareResult(display, r).to_dict() for r in raw_results]
    }


class DisplayAwareResult(object):

    def __init__(self, display, result):
        self._display = display
        self._result = result

    def to_dict(self):
        return {
            'column_values': [self._result.fields.get(d.field, d.default) for d in self._display],
            'relations': self._result.relations,
            'source': self._result.source,
        }
