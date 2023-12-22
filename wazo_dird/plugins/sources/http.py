# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from flask import request

from wazo_dird.auth import required_acl
from wazo_dird.http import AuthResource
from wazo_dird.plugin_helpers.tenant import get_tenant_uuids

from .schemas import list_schema, source_list_schema


class Sources(AuthResource):
    def __init__(self, source_service):
        self._source_service = source_service

    @required_acl('dird.sources.read')
    def get(self):
        list_params = list_schema.load(request.args)
        visible_tenants = get_tenant_uuids(recurse=list_params['recurse'])
        backend = list_params.pop('backend', None)
        sources = self._source_service.list_(backend, visible_tenants, **list_params)
        items = source_list_schema.dump(sources)
        filtered = self._source_service.count(backend, visible_tenants, **list_params)
        total = self._source_service.count(None, visible_tenants)

        return {'total': total, 'filtered': filtered, 'items': items}
