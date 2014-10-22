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
        if 'config' not in args:
            logger.error('HTTP view loaded without a config')
            return
        if 'displays' not in args['config']:
            logger.error('HTTP view loaded without a display')
            return

        lookup_fn = partial(_lookup_wrapper, args.get('services', {}), args['config'])
        args['http_app'].add_url_rule(self.ROUTE, __name__, lookup_fn)


def _lookup_wrapper(services, view_config, profile):
    def make_error(msg, code):
        return make_response(json.dumps({'reason': [msg],
                                         'timestamp': [time()],
                                         'status_code': code}), code)

    if 'lookup' not in services:
        return make_error('no lookup service available', 500)

    args = copy.copy(request.args)

    if 'term' not in args:
        return make_error('term is missing', 400)

    term = args.pop('term')

    logger.info('Lookup for %s with profile %s and args %s', term, profile, args)

    display = view_config['displays'][view_config['profile_to_display'][profile]]
    result = _lookup(services['lookup'], display, term, profile, args)
    json_result = json.dumps(result)

    return make_response(json_result, 200)


def _lookup(lookup_service, display, term, profile, args):
    raw_results = lookup_service(term, profile, args)
    return map(partial(_format_for_display, display), raw_results)


def _format_for_display(display, entry):
    result = {}
    for title, type_, default, field in display:
        result[title] = entry.get(field, default)
    return result
