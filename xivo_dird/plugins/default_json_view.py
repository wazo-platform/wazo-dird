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

from flask import request
from flask.helpers import make_response
from functools import partial
from time import time
from xivo_dird import BaseViewPlugin

logger = logging.getLogger(__name__)


class JsonViewPlugin(BaseViewPlugin):

    API_VERSION = '0.1'
    ROUTE = '/{version}/directories/lookup/<profile>'.format(version=API_VERSION)

    def load(self, args=None):
        if not args:
            args = {}

        if 'http_app' not in args:
            logger.error('HTTP view loaded with an http_app')
            return

        lookup_fn = partial(_lookup_wrapper, args.get('services', {}))
        args['http_app'].add_url_rule(self.ROUTE, __name__, lookup_fn)


def _lookup_wrapper(services, profile):
    args = copy.copy(request.args)

    if 'term' not in args:
        error_msg = {'reason': ['term is missing'],
                     'timestamp': [time()],
                     'status_code': 400}
        return make_response(json.dumps(error_msg), 400)

    term = args.pop('term')

    logger.info('Lookup for %s with profile %s and args %s', term, profile, args)

    if 'lookup' not in services:
        return make_response('[]', 200)

    result = json.dumps(services['lookup'](term, profile, args))

    return make_response(result, 200)
