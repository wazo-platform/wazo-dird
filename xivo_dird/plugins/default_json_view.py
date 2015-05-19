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
from flask_restplus import Resource
from flask_restplus import fields
from time import time

from xivo_dird import BaseViewPlugin
from xivo_dird.core.rest_api import api

logger = logging.getLogger(__name__)

parser = api.parser()
parser.add_argument('term', type=unicode, required=True, help='term is missing', location='args')


class JsonViewPlugin(BaseViewPlugin):

    def load(self, args=None):
        if 'lookup' not in args['services']:
            logger.error('Missing service plugin: lookup')
            return

        config = args['config']

        Lookup.configure(displays=make_displays(config),
                         lookup_service=args['services']['lookup'])

        api.route('/directories/lookup/<profile>', doc=doc)(Lookup)

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
            'required': True,
        },
        'profile': {
            'description': 'The profile to look for'
        }
    },
    'responses': {
        404: 'Invalid profile'
    }
}


class Lookup(Resource):
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

        raw_results = self.lookup_service(term, profile, args={})

        if profile not in self.displays:
            error = {
                'reason': ['The profile does not exist'],
                'timestamp': [time()],
                'status_code': 404,
            }
            return error, 404

        display = self.displays[profile]
        response = format_results(raw_results, display)

        response.update({'term': term})
        return response


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
