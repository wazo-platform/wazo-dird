# Copyright 2014-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from wazo_dird import BaseViewPlugin

from .http import Headers

logger = logging.getLogger(__name__)


class HeadersViewPlugin(BaseViewPlugin):

    def load(self, dependencies):
        api = dependencies['api']
        config = dependencies['config'].get('views', {})
        profile_to_display = config.get('profile_to_display', {})
        display_service = dependencies['services'].get('display')

        api.add_resource(
            Headers,
            '/directories/lookup/<profile>/headers',
            resource_class_args=(display_service, profile_to_display),
        )
