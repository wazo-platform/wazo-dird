# Copyright 2016-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from collections import namedtuple

from wazo_dird import BaseViewPlugin
from wazo_dird.rest_api import api

from .http import (
    FavoritesRead,
    FavoritesWrite,
    Lookup,
    Personal,
    Reverse,
)

logger = logging.getLogger(__name__)


class JsonViewPlugin(BaseViewPlugin):

    lookup_url = '/directories/lookup/<profile>'
    reverse_url = '/directories/reverse/<profile>/<xivo_user_uuid>'
    favorites_read_url = '/directories/favorites/<profile>'
    favorites_write_url = '/directories/favorites/<directory>/<contact>'
    personal_url = '/directories/personal/<profile>'

    def load(self, args=None):
        config = args['config'].get('views', {})
        displays = make_displays(config)

        favorite_service = args['services'].get('favorites')
        lookup_service = args['services'].get('lookup')
        reverse_service = args['services'].get('reverse')
        personal_service = args['services'].get('personal')

        if lookup_service:
            Lookup.configure(displays=displays,
                             lookup_service=lookup_service,
                             favorite_service=favorite_service)

            api.add_resource(Lookup, self.lookup_url)
        else:
            logger.error('%s disabled: no service plugin `lookup`', self.lookup_url)

        if reverse_service:
            Reverse.configure(reverse_service=reverse_service)

            api.add_resource(Reverse, self.reverse_url)
        else:
            logger.error('%s disabled: no service plugin `reverse`', self.reverse_url)

        if favorite_service:
            FavoritesRead.configure(displays=displays,
                                    favorites_service=favorite_service)
            FavoritesWrite.configure(favorites_service=favorite_service)

            api.add_resource(FavoritesRead, self.favorites_read_url)
            api.add_resource(FavoritesWrite, self.favorites_write_url)
        else:
            logger.error('%s disabled: no service plugin `favorites`', self.favorites_read_url)
            logger.error('%s disabled: no service plugin `favorites`', self.favorites_write_url)

        if personal_service:
            Personal.configure(displays=displays,
                               personal_service=personal_service,
                               favorite_service=favorite_service)
            api.add_resource(Personal, self.personal_url)
        else:
            logger.error('%s disabled: no service plugin `personal`', self.personal_url)


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
