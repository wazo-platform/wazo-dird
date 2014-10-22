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

import copy
import json
import logging

from collections import namedtuple
from flask import request
from flask.helpers import make_response
from functools import partial
from time import time
from xivo_dird import BaseViewPlugin

logger = logging.getLogger(__name__)


DisplayColumn = namedtuple('DisplayColumn', ['title', 'type', 'default', 'field'])


class JsonViewPlugin(BaseViewPlugin):

    API_VERSION = '0.1'
    ROUTE = '/{version}/directories/lookup/<profile>'.format(version=API_VERSION)

    def load(self, args=None):
        if not args:
            args = {}

        if 'http_app' not in args:
            logger.error('HTTP view loaded without an http_app')
            return
        if 'services' not in args or 'lookup' not in args['services']:
            logger.error('HTTP view loaded without a lookup service')
            return
        if 'config' not in args:
            logger.error('HTTP view loaded without a config')
            return
        if 'displays' not in args['config']:
            logger.error('HTTP view loaded without a display')
            return
        if 'profile_to_display' not in args['config']:
            logger.error('HTTP view loaded without a profile to display configuration')
            return

        lookup_fn = partial(_lookup_wrapper, args['services']['lookup'],
                            self._get_display_dict(args['config']))
        args['http_app'].add_url_rule(self.ROUTE, __name__, lookup_fn)

    def _get_display_dict(self, view_config):
        result = {}
        for profile, display_name in view_config['profile_to_display'].iteritems():
            result[profile] = view_config['displays'][display_name]
        return result


def _lookup_wrapper(lookup_service, displays, profile):
    args = copy.copy(request.args)

    if 'term' not in args:
        return make_response(json.dumps({'reason': ['term is missing'],
                                         'timestamp': [time()],
                                         'status_code': 400}), 400)

    term = args.pop('term')

    logger.info('Lookup for %s with profile %s and args %s', term, profile, args)

    result = _lookup(lookup_service, displays[profile], term, profile, args)
    json_result = json.dumps(result)

    return make_response(json_result, 200)


def _lookup(lookup_service, display, term, profile, args):
    raw_results = lookup_service(term, profile, args)
    return {
        'term': term,
        'column_headers': [d.title for d in display],
        'column_types': [d.type for d in display],
        'results': [r.to_dict() for r in raw_results]
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
