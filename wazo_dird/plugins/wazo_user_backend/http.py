# Copyright 2018-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from uuid import uuid4
from flask import request

from wazo_dird.auth import required_acl
from wazo_dird.rest_api import AuthResource
from xivo.tenant_flask_helpers import Tenant

from .schemas import source_schema

logger = logging.getLogger(__name__)


class Sources(AuthResource):

    @required_acl('dird.backends.wazo.sources.create')
    def post(self):
        tenant = Tenant.autodetect()
        args = source_schema.load(request.get_json()).data
        logger.critical('%s', args)
        logger.critical('New wazo source: %s in tenant %s', args, tenant.uuid)
        args['tenant_uuid'] = tenant.uuid
        args['uuid'] = str(uuid4())
        return source_schema.dump(args)
