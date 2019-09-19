# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from flask import request
from xivo.tenant_flask_helpers import Tenant

from wazo_dird import exception
from wazo_dird.helpers import SourceItem, SourceList
from wazo_dird.auth import required_acl
from wazo_dird.rest_api import AuthResource
from wazo_dird.plugin_helpers.confd_client_registry import registry

from .schemas import (
    contact_list_param_schema,
    contact_list_schema,
    list_schema,
    source_list_schema,
    source_schema,
)


class ConferenceList(SourceList):

    list_schema = list_schema
    source_schema = source_schema
    source_list_schema = source_list_schema

    @required_acl('dird.backends.conference.sources.read')
    def get(self):
        return super().get()

    @required_acl('dird.backends.conference.sources.create')
    def post(self):
        return super().post()


class ConferenceItem(SourceItem):

    source_schema = source_schema

    @required_acl('dird.backends.conference.sources.{source_uuid}.delete')
    def delete(self, source_uuid):
        return super().delete(source_uuid)

    @required_acl('dird.backends.conference.sources.{source_uuid}.read')
    def get(self, source_uuid):
        return super().get(source_uuid)

    @required_acl('dird.backends.conference.sources.{source_uuid}.update')
    def put(self, source_uuid):
        return super().put(source_uuid)


class ConferenceContactList(AuthResource):
    def __init__(self, source_service):
        self._source_service = source_service

    @required_acl('dird.backends.conference.sources.{source_uuid}.contacts.read')
    def get(self, source_uuid):
        tenant_uuid = Tenant.autodetect().uuid
        visible_tenants = self.get_visible_tenants(tenant_uuid)
        list_params = contact_list_param_schema.load(request.args)
        source_config = self._source_service.get(
            'conference', source_uuid, visible_tenants
        )

        confd = registry.get(source_config)
        try:
            response = confd.conferences.list(**list_params)
        except Exception as e:
            raise exception.WazoConfdError(confd, e)

        return {
            'total': response['total'],
            'filtered': response['total'],
            'items': contact_list_schema.dump(response['items']),
        }
