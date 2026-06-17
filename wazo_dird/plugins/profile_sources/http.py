# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flask import request
from xivo.tenant_flask_helpers import Tenant

from wazo_dird.auth import required_acl
from wazo_dird.http import AuthResource

from .schemas import ListSchema

if TYPE_CHECKING:
    from wazo_dird.plugins.profile_service.plugin import _ProfileService


class SourceResource(AuthResource):
    def __init__(self, profile_service: _ProfileService) -> None:
        self._profile_service = profile_service

    @required_acl('dird.directories.{profile}.sources.read')
    def get(self, profile: str) -> dict[str, Any]:
        args = ListSchema().load(request.args)
        tenant_uuid = Tenant.autodetect().uuid

        count, filtered, sources = self._profile_service.get_sources_from_profile_name(
            tenant_uuid=tenant_uuid, profile_name=profile, **args
        )

        return {'total': count, 'filtered': filtered, 'items': sources}
