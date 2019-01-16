# Copyright 2018-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from flask import request

from wazo_dird.auth import required_acl
from wazo_dird.rest_api import AuthResource
from xivo.tenant_flask_helpers import Tenant

from .schemas import source_schema

logger = logging.getLogger(__name__)


class BaseSourceResource(AuthResource):

    def __init__(self, service):
        self._service = service


class SourceList(BaseSourceResource):

    @required_acl('dird.backends.wazo.sources.create')
    def post(self):
        tenant = Tenant.autodetect()
        args = source_schema.load(request.get_json()).data
        body = self._service.create(tenant_uuid=tenant.uuid, **args)
        return source_schema.dump(body)


class SourceItem(BaseSourceResource):

    @required_acl('dird.backends.wazo.sources.{source_uuid}.read')
    def get(self, source_uuid):
        tenant = Tenant.autodetect()
        body = self._service.get(tenant.uuid, source_uuid)
        return source_schema.dump(body)
