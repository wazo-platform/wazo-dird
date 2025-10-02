# Copyright 2016-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from flask import request
from jsonpatch import JsonPatch

from wazo_dird.auth import required_acl, required_master_tenant
from wazo_dird.http import AuthResource
from wazo_dird.plugins.config_service.plugin import Service as ConfigService

from .schemas import config_patch_schema


class Config(AuthResource):
    def __init__(self, config_service: ConfigService) -> None:
        self._config_service = config_service

    @required_master_tenant()
    @required_acl('dird.config.read')
    def get(self) -> dict:
        config = self._config_service.get_config()
        return dict(config)

    @required_master_tenant()
    @required_acl('dird.config.update')
    def patch(self) -> tuple[dict, int]:
        config_patch = config_patch_schema.load(request.get_json(), many=True)
        config = self._config_service.get_config()
        patched_config = JsonPatch(config_patch).apply(config)
        self._config_service.update_config(patched_config)
        return dict(self._config_service.get_config()), 200
