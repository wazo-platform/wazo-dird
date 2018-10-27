# Copyright 2014-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from collections import namedtuple
from time import time

from wazo_dird import BaseViewPlugin
from wazo_dird.auth import required_acl
from wazo_dird.rest_api import api
from wazo_dird.rest_api import AuthResource

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

    @required_acl('dird.directories.lookup.{profile}.headers.read')
    def get(self, profile):
        logger.debug('header request on profile %s', profile)
        if profile not in self.displays:
            logger.warning('profile %s does not exist, or associated display does not exist', profile)
            error = {
                'reason': ['The profile `{profile}` does not exist'.format(profile=profile)],
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
    for profile, display_name in view_config.get('profile_to_display', {}).items():
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
