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

from .schemas import list_schema, profile_list_schema, profile_schema

if TYPE_CHECKING:
    from wazo_dird.plugins.profile_service.plugin import _ProfileService

logger = logging.getLogger(__name__)


class _BaseResource(AuthResource):
    def __init__(self, profile_service: _ProfileService) -> None:
        self._profile_service = profile_service


class Profiles(_BaseResource):
    @required_acl('dird.profiles.read')
    def get(self) -> dict[str, Any]:
        list_params = list_schema.load(request.args)
        visible_tenants = get_tenant_uuids(recurse=list_params['recurse'])
        profiles = self._profile_service.list_(visible_tenants, **list_params)
        items = profile_list_schema.dump(profiles)
        filtered = self._profile_service.count(visible_tenants, **list_params)
        total = self._profile_service.count(visible_tenants)

        return {'total': total, 'filtered': filtered, 'items': items}

    @required_acl('dird.profiles.create')
    def post(self) -> tuple[dict[str, Any], int]:
        tenant = Tenant.autodetect()
        args = profile_schema.load(get_json_body())
        body = self._profile_service.create(tenant_uuid=tenant.uuid, **args)
        result: dict[str, Any] = profile_schema.dump(body)
        return result, 201


class Profile(_BaseResource):
    @required_acl('dird.profiles.{profile_uuid}.delete')
    def delete(self, profile_uuid: str) -> tuple[str, int]:
        visible_tenants = get_tenant_uuids(recurse=True)
        self._profile_service.delete(profile_uuid, visible_tenants)
        return '', 204

    @required_acl('dird.profiles.{profile_uuid}.read')
    def get(self, profile_uuid: str) -> dict[str, Any]:
        visible_tenants = get_tenant_uuids(recurse=True)
        profile = self._profile_service.get(profile_uuid, visible_tenants)
        result: dict[str, Any] = profile_schema.dump(profile)
        return result

    @required_acl('dird.profiles.{profile_uuid}.update')
    def put(self, profile_uuid: str) -> tuple[str, int]:
        visible_tenants = get_tenant_uuids(recurse=True)
        args = profile_schema.load(get_json_body())
        self._profile_service.edit(
            profile_uuid, visible_tenants=visible_tenants, **args
        )
        return '', 204
