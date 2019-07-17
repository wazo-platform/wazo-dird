# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from flask import request
from wazo_dird.auth import required_acl
from wazo_dird.helpers import SourceItem, SourceList
from wazo_dird.rest_api import AuthResource
from xivo.tenant_flask_helpers import Tenant, token

from .schemas import list_schema, source_list_schema, source_schema
from .services import Office365Service, get_microsoft_access_token

logger = logging.getLogger(__name__)


class MicrosoftContactList(AuthResource):

    BACKEND = 'office365'

    def __init__(self, auth_config, config, source_service):
        self.auth_config = auth_config
        self.config = config
        self.source_service = source_service
        self.office365 = Office365Service()

    @required_acl('dird.backends.office365.sources.{source_uuid}.contacts.read')
    def get(self, source_uuid):
        user_uuid = token.user_uuid
        token_from_request = request.headers.get('X-Auth-Token')
        tenant = Tenant.autodetect()

        source = self.source_service.get(self.BACKEND, source_uuid, [tenant.uuid])
        microsoft_token = get_microsoft_access_token(user_uuid, token_from_request, **source['auth'])

        contacts = self.office365.get_contacts(microsoft_token, source['endpoint'])

        return {
            'filtered': len(contacts),
            'items': contacts,
            'total': len(contacts),
        }, 200


class MicrosoftList(SourceList):

    list_schema = list_schema
    source_schema = source_schema
    source_list_schema = source_list_schema

    @required_acl('dird.backends.office365.sources.read')
    def get(self):
        return super().get()

    @required_acl('dird.backends.office365.sources.create')
    def post(self):
        return super().post()


class MicrosoftItem(SourceItem):

    source_schema = source_schema

    @required_acl('dird.backends.office365.sources.{source_uuid}.delete')
    def delete(self, source_uuid):
        return super().delete(source_uuid)

    @required_acl('dird.backends.office365.sources.{source_uuid}.read')
    def get(self, source_uuid):
        return super().get(source_uuid)

    @required_acl('dird.backends.office365.sources.{source_uuid}.update')
    def put(self, source_uuid):
        return super().put(source_uuid)
