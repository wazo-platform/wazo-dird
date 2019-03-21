# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from flask import request
from xivo.tenant_flask_helpers import (
    Tenant,
    token,
)

from wazo_dird.auth import required_acl
from wazo_dird.rest_api import AuthResource

from .schemas import (
    display_list_schema,
    display_schema,
    list_schema,
)

logger = logging.getLogger(__name__)


class _BaseResource(AuthResource):

    def __init__(self, display_service):
        self._display_service = display_service


class Displays(_BaseResource):

    @required_acl('dird.displays.read')
    def get(self):
        list_params, errors = list_schema.load(request.args)
        if list_params['recurse']:
            visible_tenants = [tenant.uuid for tenant in token.visible_tenants()]
        else:
            visible_tenants = [Tenant.autodetect().uuid]

        displays = self._display_service.list_(visible_tenants, **list_params)
        items, errors = display_list_schema.dump(displays)
        filtered = self._display_service.count(visible_tenants, **list_params)
        total = self._display_service.count(visible_tenants)

        return {
            'total': total,
            'filtered': filtered,
            'items': items,
        }

    @required_acl('dird.displays.create')
    def post(self):
        tenant = Tenant.autodetect()
        args = display_schema.load(request.get_json()).data
        body = self._display_service.create(tenant_uuid=tenant.uuid, **args)
        return display_schema.dump(body).data, 201


class Display(_BaseResource):

    @required_acl('dird.displays.{display_uuid}.delete')
    def delete(self, display_uuid):
        visible_tenants = [tenant.uuid for tenant in token.visible_tenants()]
        self._display_service.delete(display_uuid, visible_tenants)
        return '', 204

    @required_acl('dird.displays.{display_uuid}.read')
    def get(self, display_uuid):
        pass

    @required_acl('dird.displays.{display_uuid}.update')
    def put(self, display_uuid):
        pass
