# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from flask import request
from xivo.tenant_flask_helpers import Tenant

from wazo_dird.auth import required_acl
from wazo_dird.rest_api import AuthResource

from .schemas import source_list_schema, list_schema


class Sources(AuthResource):
    def __init__(self, source_service):
        self._source_service = source_service

    @required_acl('dird.sources.read')
    def get(self):
        list_params, errors = list_schema.load(request.args)
        tenant_uuid = Tenant.autodetect().uuid
        if list_params['recurse']:
            visible_tenants = self.get_visible_tenants(tenant_uuid)
        else:
            visible_tenants = [tenant_uuid]

        backend = list_params.pop('backend', None)
        sources = self._source_service.list_(backend, visible_tenants, **list_params)
        items, errors = source_list_schema.dump(sources)
        filtered = self._source_service.count(backend, visible_tenants, **list_params)
        total = self._source_service.count(None, visible_tenants)

        return {'total': total, 'filtered': filtered, 'items': items}
