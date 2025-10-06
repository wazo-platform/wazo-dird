# Copyright 2016-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from typing import Any

from wazo_dird import BaseViewPlugin

from .http import Config

logger = logging.getLogger(__name__)

# TODO: replace with TypedDict
HTTPDependencies = dict[str, Any]


class ConfigViewPlugin(BaseViewPlugin):
    url = "/config"

    def load(self, dependencies: HTTPDependencies) -> None:
        api = dependencies["api"]
        config_service = dependencies["services"].get("config")
        if not config_service:
            logger.info(
                "failed to load the %s config service is disabled",
                self.__class__.__name__,
            )
            return

        api.add_resource(Config, self.url, resource_class_args=[config_service])
