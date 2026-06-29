# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from flask import request
from xivo.tenant_flask_helpers import Tenant

from wazo_dird.auth import required_acl
from wazo_dird.http import AuthResource, get_json_body
from wazo_dird.plugin_helpers.tenant import get_tenant_uuids

from .schemas import display_list_schema, display_schema, list_schema

if TYPE_CHECKING:
    from wazo_dird.plugins.display_service.plugin import _DisplayService

logger = logging.getLogger(__name__)


class _BaseResource(AuthResource):
    def __init__(self, display_service: _DisplayService) -> None:
        self._display_service = display_service


class Displays(_BaseResource):
    @required_acl('dird.displays.read')
    def get(self) -> dict[str, Any]:
        list_params = list_schema.load(request.args)
        visible_tenants = get_tenant_uuids(recurse=list_params['recurse'])
        displays = self._display_service.list_(visible_tenants, **list_params)
        items = display_list_schema.dump(displays)
        filtered = self._display_service.count(visible_tenants, **list_params)
        total = self._display_service.count(visible_tenants)

        return {'total': total, 'filtered': filtered, 'items': items}

    @required_acl('dird.displays.create')
    def post(self) -> tuple[dict[str, Any], int]:
        tenant = Tenant.autodetect()
        args = display_schema.load(get_json_body())
        body = self._display_service.create(tenant_uuid=tenant.uuid, **args)
        result: dict[str, Any] = display_schema.dump(body)
        return result, 201


class Display(_BaseResource):
    @required_acl('dird.displays.{display_uuid}.delete')
    def delete(self, display_uuid: str) -> tuple[str, int]:
        visible_tenants = get_tenant_uuids(recurse=True)
        self._display_service.delete(display_uuid, visible_tenants)
        return '', 204

    @required_acl('dird.displays.{display_uuid}.read')
    def get(self, display_uuid: str) -> dict[str, Any]:
        visible_tenants = get_tenant_uuids(recurse=True)
        display = self._display_service.get(display_uuid, visible_tenants)
        result: dict[str, Any] = display_schema.dump(display)
        return result

    @required_acl('dird.displays.{display_uuid}.update')
    def put(self, display_uuid: str) -> tuple[str, int]:
        visible_tenants = get_tenant_uuids(recurse=True)
        args = display_schema.load(get_json_body())
        self._display_service.edit(
            display_uuid, visible_tenants=visible_tenants, **args
        )
        return '', 204
