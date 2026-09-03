# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from flask import request

from wazo_dird.auth import required_acl, required_master_tenant
from wazo_dird.http import AuthResource

from .service import FavoriteMigrationService, MigrationReport


class FavoriteMigrationResource(AuthResource):
    def __init__(self, service: FavoriteMigrationService) -> None:
        self._service = service

    @required_master_tenant()
    @required_acl('dird.favorite_migration.create')
    def post(self) -> tuple[MigrationReport, int]:
        return self._service.migrate(request.headers['X-Auth-Token']), 200
