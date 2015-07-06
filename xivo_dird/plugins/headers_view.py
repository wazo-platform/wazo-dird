# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2015 Avencall
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
from time import time

from xivo_dird import BaseViewPlugin
from xivo_dird.core.auth import AuthResource
from xivo_dird.core.rest_api import api

logger = logging.getLogger(__name__)


class HeadersViewPlugin(BaseViewPlugin):

    def load(self, args):
        config = args['config']
        displays = make_displays(config)
        Headers.configure(displays)

        api.add_resource(Headers, '/directories/lookup/<profile>/headers')


class Headers(AuthResource):
    displays = None

    @classmethod
    def configure(cls, displays):
        cls.displays = displays

    def get(self, profile):
        logger.debug('header request on profile %s', profile)
        if profile not in self.displays:
            logger.warning('profile %s does not exist, or associated display does not exist', profile)
            error = {
                'reason': ['The profile does not exist'],
                'timestamp': [time()],
                'status_code': 404,
            }
            return error, 404

        display = self.displays[profile]
        response = format_headers(display)
        return response


def format_headers(display):
    return {
        'column_headers': [d.title for d in display],
        'column_types': [d.type for d in display],
    }


def make_displays(view_config):
    result = {}
    for profile, display_name in view_config.get('profile_to_display', {}).iteritems():
        result[profile] = _make_display_from_name(view_config, display_name)
    return result


def _make_display_from_name(view_config, display_name):
    if display_name not in view_config['displays']:
        logger.warning('Display `%s` is not defined.', display_name)
    display = view_config['displays'].get(display_name, [])
    return [
        DisplayColumn(column.get('title'),
                      column.get('type'),
                      column.get('default'),
                      column.get('field'))
        for column in display
    ]

DisplayColumn = namedtuple('DisplayColumn', ['title', 'type', 'default', 'field'])
