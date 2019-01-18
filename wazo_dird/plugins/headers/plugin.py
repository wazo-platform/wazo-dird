# Copyright 2014-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from collections import namedtuple

from wazo_dird import BaseViewPlugin

from .http import Headers

logger = logging.getLogger(__name__)


class HeadersViewPlugin(BaseViewPlugin):

    def load(self, dependencies):
        api = dependencies['api']
        config = dependencies['config'].get('views', {})
        displays = make_displays(config)
        Headers.configure(displays)

        api.add_resource(Headers, '/directories/lookup/<profile>/headers')


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
