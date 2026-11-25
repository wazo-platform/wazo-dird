# Copyright 2018-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from flask import request

from wazo_dird.auth import required_acl
from wazo_dird.exception import NoSuchSource
from wazo_dird.helpers import SourceItem, SourceList
from wazo_dird.http import AuthResource
from wazo_dird.plugin_helpers.tenant import get_tenant_uuids
from wazo_dird.plugins.source_service.plugin import _SourceService

from .schemas import (
    contact_list_param_schema,
    contact_list_schema,
    list_schema,
    source_list_schema,
    source_schema,
)

if TYPE_CHECKING:
    from .plugin import WazoUserPlugin


class WazoList(SourceList):
    list_schema = list_schema
    source_schema = source_schema
    source_list_schema = source_list_schema

    @required_acl('dird.backends.wazo.sources.read')
    def get(self) -> dict[str, Any]:
        return super().get()

    @required_acl('dird.backends.wazo.sources.create')
    def post(self) -> dict[str, Any]:
        return super().post()


class WazoItem(SourceItem):
    source_schema = source_schema

    @required_acl('dird.backends.wazo.sources.{source_uuid}.delete')
    def delete(self, source_uuid: str) -> tuple[str, int]:
        return super().delete(source_uuid)

    @required_acl('dird.backends.wazo.sources.{source_uuid}.read')
    def get(self, source_uuid: str) -> dict[str, Any]:
        return super().get(source_uuid)

    @required_acl('dird.backends.wazo.sources.{source_uuid}.update')
    def put(self, source_uuid: str) -> tuple[str, int]:
        return super().put(source_uuid)


class WazoContactList(AuthResource):
    def __init__(self, source_service: _SourceService) -> None:
        self._source_service = source_service

    @required_acl('dird.backends.wazo.sources.{source_uuid}.contacts.read')
    def get(self, source_uuid: str) -> dict[str, Any]:
        visible_tenants = get_tenant_uuids(recurse=True)
        list_params = contact_list_param_schema.load(request.args)
        self._source_service.get('wazo', source_uuid, visible_tenants)

        source = self._source_service.get_plugin(source_uuid)
        if source is None:  # deleted since the check above
            raise NoSuchSource(source_uuid)
        response = cast('WazoUserPlugin', source).list_contacts(**list_params)

        return {
            'total': response['total'],
            'filtered': response['total'],
            'items': contact_list_schema.dump(response['items']),
        }
