# Copyright 2016-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from wazo_dird import BaseViewPlugin

from .http import FavoritesRead, FavoritesWrite, Lookup, LookupByUUID, Personal, Reverse

logger = logging.getLogger(__name__)


class JsonViewPlugin(BaseViewPlugin):
    lookup_url = '/directories/lookup/<profile>'
    uuid_lookup_url = '/directories/lookup/<profile>/<user_uuid>'
    reverse_url = '/directories/reverse/<profile>/<user_uuid>'
    favorites_read_url = '/directories/favorites/<profile>'
    favorites_write_url = '/directories/favorites/<path:directory>/<contact>'
    personal_url = '/directories/personal/<profile>'

    def load(self, dependencies):
        api = dependencies['api']
        favorite_service = dependencies['services'].get('favorites')
        lookup_service = dependencies['services'].get('lookup')
        reverse_service = dependencies['services'].get('reverse')
        personal_service = dependencies['services'].get('personal')
        profile_service = dependencies['services'].get('profile')
        display_service = dependencies['services'].get('display')
        auth_client = dependencies['auth_client']

        if lookup_service:
            api.add_resource(
                Lookup,
                self.lookup_url,
                resource_class_args=(
                    lookup_service,
                    favorite_service,
                    display_service,
                    profile_service,
                ),
            )
            api.add_resource(
                LookupByUUID,
                self.uuid_lookup_url,
                resource_class_args=(
                    lookup_service,
                    favorite_service,
                    display_service,
                    profile_service,
                    auth_client,
                ),
            )
        else:
            logger.error('%s disabled: no service plugin `lookup`', self.lookup_url)

        if reverse_service:
            api.add_resource(
                Reverse,
                self.reverse_url,
                resource_class_args=(reverse_service, profile_service),
            )
        else:
            logger.error('%s disabled: no service plugin `reverse`', self.reverse_url)

        if favorite_service:
            api.add_resource(
                FavoritesRead,
                self.favorites_read_url,
                resource_class_args=(
                    favorite_service,
                    display_service,
                    profile_service,
                ),
            )
            api.add_resource(
                FavoritesWrite,
                self.favorites_write_url,
                resource_class_args=(favorite_service,),
            )
        else:
            logger.error(
                '%s disabled: no service plugin `favorites`', self.favorites_read_url
            )
            logger.error(
                '%s disabled: no service plugin `favorites`', self.favorites_write_url
            )

        if personal_service:
            api.add_resource(
                Personal,
                self.personal_url,
                resource_class_args=(
                    personal_service,
                    favorite_service,
                    display_service,
                    profile_service,
                ),
            )
        else:
            logger.error('%s disabled: no service plugin `personal`', self.personal_url)
