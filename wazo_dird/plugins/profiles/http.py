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
    list_schema,
    profile_list_schema,
    profile_schema,
)

logger = logging.getLogger(__name__)


class _BaseResource(AuthResource):

    def __init__(self, profile_service):
        self._profile_service = profile_service


class Profiles(_BaseResource):

    @required_acl('dird.profiles.read')
    def get(self):
        list_params, errors = list_schema.load(request.args)
        tenant_uuid = Tenant.autodetect().uuid
        if list_params['recurse']:
            visible_tenants = self.get_visible_tenants(tenant_uuid)
        else:
            visible_tenants = [tenant_uuid]

        profiles = self._profile_service.list_(visible_tenants, **list_params)
        items, errors = profile_list_schema.dump(profiles)
        filtered = self._profile_service.count(visible_tenants, **list_params)
        total = self._profile_service.count(visible_tenants)

        return {
            'total': total,
            'filtered': filtered,
            'items': items,
        }

    @required_acl('dird.profiles.create')
    def post(self):
        tenant = Tenant.autodetect()
        args = profile_schema.load(request.get_json()).data
        body = self._profile_service.create(tenant_uuid=tenant.uuid, **args)
        return profile_schema.dump(body).data, 201


class Profile(_BaseResource):

    @required_acl('dird.profiles.{profile_uuid}.delete')
    def delete(self, profile_uuid):
        tenant_uuid = Tenant.autodetect().uuid
        visible_tenants = self.get_visible_tenants(tenant_uuid)
        self._profile_service.delete(profile_uuid, visible_tenants)
        return '', 204

    @required_acl('dird.profiles.{profile_uuid}.read')
    def get(self, profile_uuid):
        tenant_uuid = Tenant.autodetect().uuid
        visible_tenants = self.get_visible_tenants(tenant_uuid)
        profile = self._profile_service.get(profile_uuid, visible_tenants)
        return profile_schema.dump(profile).data

    @required_acl('dird.profiles.{profile_uuid}.update')
    def put(self, profile_uuid):
        tenant_uuid = Tenant.autodetect().uuid
        visible_tenants = self.get_visible_tenants(tenant_uuid)
        args = profile_schema.load(request.get_json()).data
        self._profile_service.edit(profile_uuid, visible_tenants=visible_tenants, **args)
        return '', 204
