# Copyright 2019-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from flask import request
from wazo_dird.auth import required_acl
from wazo_dird.http_server import AuthResource
from xivo.tenant_flask_helpers import Tenant

from .schemas import ListSchema


class SourceResource(AuthResource):
    def __init__(self, profile_service):
        self._profile_service = profile_service

    @required_acl('dird.directories.{profile}.sources.read')
    def get(self, profile):
        args = ListSchema().load(request.args)
        tenant_uuid = Tenant.autodetect().uuid

        count, filtered, sources = self._profile_service.get_sources_from_profile_name(
            tenant_uuid=tenant_uuid, profile_name=profile, **args
        )

        return {'total': count, 'filtered': filtered, 'items': sources}
