# Copyright 2014-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from xivo.tenant_flask_helpers import Tenant

from wazo_dird.auth import required_acl
from wazo_dird.exception import OldAPIException
from wazo_dird.helpers import DisplayAwareResource, DisplayColumn
from wazo_dird.http import LegacyAuthResource

if TYPE_CHECKING:
    from wazo_dird.plugins.display_service.plugin import _DisplayService
    from wazo_dird.plugins.profile_service.plugin import _ProfileService

logger = logging.getLogger(__name__)


class Headers(LegacyAuthResource, DisplayAwareResource):
    def __init__(
        self, display_service: _DisplayService, profile_service: _ProfileService
    ) -> None:
        self.display_service = display_service
        self.profile_service = profile_service

    @required_acl('dird.directories.lookup.{profile}.headers.read')
    def get(self, profile: str) -> dict[str, Any] | tuple[dict[str, Any], int]:
        logger.debug('header request on profile %s', profile)
        tenant = Tenant.autodetect()
        try:
            profile_config = self.profile_service.get_by_name(tenant.uuid, profile)
            display = self.build_display(profile_config)
        except OldAPIException as e:
            return e.body, e.status_code
        response = format_headers(display)
        return response


def format_headers(display: list[DisplayColumn] | None) -> dict[str, Any]:
    columns = display or []
    return {
        'column_headers': [d.title for d in columns],
        'column_types': [d.type for d in columns],
    }
