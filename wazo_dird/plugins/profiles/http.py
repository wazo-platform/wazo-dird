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
    profile_schema,
)

logger = logging.getLogger(__name__)


class _BaseResource(AuthResource):

    def __init__(self, profile_service):
        self._profile_service = profile_service


class Profiles(_BaseResource):

    @required_acl('dird.profiles.create')
    def post(self):
        tenant = Tenant.autodetect()
        args = profile_schema.load(request.get_json()).data
        from pprint import pformat
        body = self._profile_service.create(tenant_uuid=tenant.uuid, **args)
        logger.critical('%s', pformat(args))
        return profile_schema.dump(body).data, 201


class Profile(_BaseResource):

    @required_acl('dird.profiles.{profile_uuid}.delete')
    def delete(self, profile_uuid):
        visible_tenants = [tenant.uuid for tenant in token.visible_tenants()]
        self._profile_service.delete(profile_uuid, visible_tenants)
        return '', 204

    @required_acl('dird.profiles.{profile_uuid}.read')
    def get(self, profile_uuid):
        visible_tenants = [tenant.uuid for tenant in token.visible_tenants()]
        profile = self._profile_service.get(profile_uuid, visible_tenants)
        return profile_schema.dump(profile).data

    @required_acl('dird.profiles.{profile_uuid}.update')
    def put(self, profile_uuid):
        visible_tenants = [tenant.uuid for tenant in token.visible_tenants()]
        args = profile_schema.load(request.get_json()).data
        self._profile_service.edit(profile_uuid, visible_tenants=visible_tenants, **args)
        return '', 204
