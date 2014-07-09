# -*- coding: utf-8 -*-

# Copyright (C) 2012-2014 Avencall
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

import json
import logging

from flask import Flask
from flask.helpers import make_response

logger = logging.getLogger(__name__)
app = Flask(__name__)

VERSION = 0.1


@app.route('/{version}/directories/lookup/<profile>/headers'.format(version=VERSION))
def headers(profile):
    logger.info('profile {} headers'.format(profile))
    dummy = json.dumps(
        {'column_headers': ['Firstname', 'Lastname', 'Phone number'],
         'column_types': [None, None, 'office']}
    )
    return make_response(dummy, 200)


@app.route('/{version}/directories/lookup/<profile>'.format(version=VERSION))
def lookup(profile):
    logger.info('profile {} lookup'.format(profile))
    return make_response('', 201)


@app.route('/{version}/directories/reverse_lookup'.format(version=VERSION))
def reverse_lookup():
    logger.info('reverse lookup')
    return make_response('', 201)
