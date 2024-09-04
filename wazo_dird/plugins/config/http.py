# Copyright 2016-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from flask import request
from jsonpatch import JsonPatch

from wazo_dird.auth import required_acl, required_master_tenant
from wazo_dird.http import AuthResource

from .schemas import config_patch_schema


class Config(AuthResource):
    _config_service = None

    @classmethod
    def configure(cls, config_service):
        cls._config_service = config_service

    @required_master_tenant()
    @required_acl('dird.config.read')
    def get(self):
        config = self._config_service.get_config()
        return dict(config)

    @required_master_tenant()
    @required_acl('dird.config.update')
    def patch(self):
        config_patch = config_patch_schema.load(request.get_json(), many=True)
        config = self._config_service.get_config()
        patched_config = JsonPatch(config_patch).apply(config)
        self._config_service.update_config(patched_config)
        return dict(self._config_service.get_config()), 200
