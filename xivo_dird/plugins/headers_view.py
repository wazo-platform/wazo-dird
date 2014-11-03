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

from time import time
from xivo_dird import BaseViewPlugin
from flask_restplus import Resource
from flask_restplus import fields

logger = logging.getLogger(__name__)


class HeadersViewPlugin(BaseViewPlugin):

    def load(self, args):
        api = args['rest_api']
        config = args['config']
        namespace = args['http_namespace']

        api_class = make_api_class(config, namespace, api)

        route = '/lookup/<profile>/headers'
        doc = {
            'model': api.model('Headers', {
                'column_headers': fields.List(fields.String,
                                              description='The labels for the result header'),
                'column_types': fields.List(fields.String,
                                            description='The types for the result header'),
            }),
            'params': {
                'profile': 'The profile identifies the list of contact sources and the display format',
            },
            'responses': {
                404: 'Invalid profile'
            }
        }

        api_class = namespace.route(route, doc=doc)(api_class)


def make_api_class(config, namespace, api):

    class Headers(Resource):

        def get(self, profile):
            logger.debug('header request on profile %s', profile)
            try:
                display_name = config.get('profile_to_display', {})[profile]
                display_configuration = config.get('displays', {})[display_name]
            except KeyError:
                logger.warning('profile %s does not exist, or associated display does not exist', profile)
                error = {
                    'reason': ['The lookup profile does not exist'],
                    'timestamp': [time()],
                    'status_code': 404,
                }
                return error, 404

            response = {'column_headers': [column.get('title') for column in display_configuration],
                        'column_types': [column.get('type') for column in display_configuration]}
            return response

    return Headers
