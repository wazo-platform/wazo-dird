# Copyright 2018-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from flask import request

from xivo.tenant_flask_helpers import Tenant
from wazo_dird.auth import required_acl
from wazo_dird.helpers import BaseSourceResource

from .schemas import (
    list_schema,
    source_schema,
)

logger = logging.getLogger(__name__)


class SourceList(BaseSourceResource):

    @required_acl('dird.backends.wazo.sources.read')
    def get(self):
        list_params, errors = list_schema.load(request.args)
        tenant = Tenant.autodetect()
        if list_params['recurse']:
            visible_tenants = self._get_visible_tenants(tenant.uuid)
        else:
            visible_tenants = [tenant.uuid]

        backends = self._service.list_(visible_tenants, **list_params)
        filtered = self._service.count(visible_tenants, **list_params)
        total = self._service.count(visible_tenants)

        return {
            'total': total,
            'filtered': filtered,
            'items': backends,
        }

    @required_acl('dird.backends.wazo.sources.create')
    def post(self):
        tenant = Tenant.autodetect()
        args = source_schema.load(request.get_json()).data
        body = self._service.create(tenant_uuid=tenant.uuid, **args)
        return source_schema.dump(body)


class SourceItem(BaseSourceResource):

    @required_acl('dird.backends.wazo.sources.{source_uuid}.delete')
    def delete(self, source_uuid):
        tenant = Tenant.autodetect()
        visible_tenants = self._get_visible_tenants(tenant.uuid)
        self._service.delete(source_uuid, visible_tenants)
        return '', 204

    @required_acl('dird.backends.wazo.sources.{source_uuid}.read')
    def get(self, source_uuid):
        tenant = Tenant.autodetect()
        visible_tenants = self._get_visible_tenants(tenant.uuid)
        body = self._service.get(source_uuid, visible_tenants)
        return source_schema.dump(body)

    @required_acl('dird.backends.wazo.sources.{source_uuid}.update')
    def put(self, source_uuid):
        tenant = Tenant.autodetect()
        visible_tenants = self._get_visible_tenants(tenant.uuid)
        args = source_schema.load(request.get_json()).data
        body = self._service.edit(source_uuid, visible_tenants, args)
        return source_schema.dump(body)
