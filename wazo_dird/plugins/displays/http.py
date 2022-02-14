# Copyright 2019-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from flask import request
from xivo.tenant_flask_helpers import Tenant

from wazo_dird.auth import required_acl
from wazo_dird.http import AuthResource

from .schemas import display_list_schema, display_schema, list_schema

logger = logging.getLogger(__name__)


class _BaseResource(AuthResource):
    def __init__(self, display_service):
        self._display_service = display_service


class Displays(_BaseResource):
    @required_acl('dird.displays.read')
    def get(self):
        list_params = list_schema.load(request.args)
        tenant_uuid = Tenant.autodetect().uuid
        if list_params['recurse']:
            visible_tenants = self.get_visible_tenants(tenant_uuid)
        else:
            visible_tenants = [tenant_uuid]

        displays = self._display_service.list_(visible_tenants, **list_params)
        items = display_list_schema.dump(displays)
        filtered = self._display_service.count(visible_tenants, **list_params)
        total = self._display_service.count(visible_tenants)

        return {'total': total, 'filtered': filtered, 'items': items}

    @required_acl('dird.displays.create')
    def post(self):
        tenant = Tenant.autodetect()
        args = display_schema.load(request.get_json())
        body = self._display_service.create(tenant_uuid=tenant.uuid, **args)
        return display_schema.dump(body), 201


class Display(_BaseResource):
    @required_acl('dird.displays.{display_uuid}.delete')
    def delete(self, display_uuid):
        tenant_uuid = Tenant.autodetect().uuid
        visible_tenants = self.get_visible_tenants(tenant_uuid)
        self._display_service.delete(display_uuid, visible_tenants)
        return '', 204

    @required_acl('dird.displays.{display_uuid}.read')
    def get(self, display_uuid):
        tenant_uuid = Tenant.autodetect().uuid
        visible_tenants = self.get_visible_tenants(tenant_uuid)
        display = self._display_service.get(display_uuid, visible_tenants)
        return display_schema.dump(display)

    @required_acl('dird.displays.{display_uuid}.update')
    def put(self, display_uuid):
        tenant_uuid = Tenant.autodetect().uuid
        visible_tenants = self.get_visible_tenants(tenant_uuid)
        args = display_schema.load(request.get_json())
        self._display_service.edit(
            display_uuid, visible_tenants=visible_tenants, **args
        )
        return '', 204
