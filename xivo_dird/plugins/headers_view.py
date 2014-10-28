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
import json

from time import time
from xivo_dird import BaseViewPlugin
from flask.helpers import make_response

logger = logging.getLogger(__name__)


class HeadersViewPlugin(BaseViewPlugin):

    API_VERSION = '0.1'
    ROUTE = '/{version}/directories/lookup/<profile>/headers'.format(version=API_VERSION)

    def load(self, args):
        self.config = args['config']
        self.http_app = args['http_app']
        self.http_app.add_url_rule(self.ROUTE, __name__, self._header)

    def _header(self, profile):
        logger.debug('header request on profile %s', profile)
        try:
            display_name = self.config.get('profile_to_display', {})[profile]
            display_configuration = self.config.get('displays', {})[display_name]
        except KeyError:
            logger.debug('Returning a 404')
            return make_response(json.dumps({
                'reason': ['The lookup profile does not exist'],
                'timestamp': [time()],
                'status_code': 404,
            }), 404)

        response = {'column_headers': [column.get('title') for column in display_configuration],
                    'column_types': [column.get('type') for column in display_configuration]}
        return make_response(json.dumps(response), 200)
