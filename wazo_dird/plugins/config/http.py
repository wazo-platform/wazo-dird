# Copyright 2016-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird.auth import required_acl, required_master_tenant
from wazo_dird.http import AuthResource
from wazo_dird.plugins.config_service.plugin import Service as ConfigService


class Config(AuthResource):
    _config_service: ConfigService

    @classmethod
    def configure(cls, config_service: ConfigService):
        cls._config_service = config_service

    @required_master_tenant()
    @required_acl('dird.config.read')
    def get(self):
        config = self._config_service.get_current_config()
        return dict(config)
