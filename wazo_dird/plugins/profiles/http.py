# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from flask import request
from xivo.tenant_flask_helpers import (
    Tenant,
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
