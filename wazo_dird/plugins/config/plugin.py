# Copyright 2016-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from wazo_dird import BaseViewPlugin

from .http import Config


logger = logging.getLogger(__name__)


class ConfigViewPlugin(BaseViewPlugin):
    url = '/config'

    def load(self, dependencies):
        api = dependencies['api']
        config_service = dependencies['services'].get('config')
        if not config_service:
            logger.info(
                'failed to load the %s config service is disabled',
                self.__class__.__name__,
            )
            return

        Config.configure(config_service)

        api.add_resource(Config, self.url)
