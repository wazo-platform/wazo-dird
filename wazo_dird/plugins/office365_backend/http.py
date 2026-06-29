# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, cast

from flask import request
from xivo.tenant_flask_helpers import Tenant, token

from wazo_dird.auth import required_acl
from wazo_dird.database.queries.source import SourceInfo
from wazo_dird.helpers import AuthConfig, SourceItem, SourceList
from wazo_dird.http import AuthResource
from wazo_dird.plugins.source_service.plugin import _SourceService

from .schemas import contact_list_schema, list_schema, source_list_schema, source_schema
from .services import Office365Service, get_microsoft_access_token

logger = logging.getLogger(__name__)


class _Office365Source(SourceInfo):
    auth: AuthConfig
    endpoint: str


class MicrosoftContactList(AuthResource):
    BACKEND = 'office365'

    def __init__(
        self,
        auth_config: AuthConfig,
        config: dict[str, Any],
        source_service: _SourceService,
    ) -> None:
        self.auth_config = auth_config
        self.config = config
        self.source_service = source_service
        self.office365 = Office365Service()

    def _map_list_params(self, list_params: Mapping[str, Any]) -> dict[str, Any]:
        schema_params: dict[str, Any] = {}
        order_mapping = {
            'firstname': 'givenName',
            'lastname': 'surname',
            'name': 'displayName',
        }
        order = list_params.get('order')
        if order:
            schema_params['order'] = order_mapping.get(order)
        limit = list_params.get('limit')
        if limit:
            schema_params['limit'] = limit
        offset = list_params.get('offset')
        if offset:
            schema_params['offset'] = offset
        direction = list_params.get('direction')
        if direction:
            schema_params['direction'] = direction
        return schema_params

    @required_acl('dird.backends.office365.sources.{source_uuid}.contacts.read')
    def get(self, source_uuid: str) -> tuple[dict[str, Any], int]:
        user_uuid = token.user_uuid
        token_from_request = request.headers.get('X-Auth-Token')
        tenant = Tenant.autodetect()
        list_params = contact_list_schema.load(self._map_list_params(request.args))

        source = cast(
            _Office365Source,
            self.source_service.get(self.BACKEND, source_uuid, [tenant.uuid]),
        )
        microsoft_token = cast(
            'str',
            get_microsoft_access_token(user_uuid, token_from_request, **source['auth']),
        )

        contacts, total = self.office365.get_contacts(
            microsoft_token, source['endpoint'], **list_params
        )

        return (
            {'filtered': total, 'items': contacts, 'total': total},
            200,
        )


class MicrosoftList(SourceList):
    list_schema = list_schema
    source_schema = source_schema
    source_list_schema = source_list_schema

    @required_acl('dird.backends.office365.sources.read')
    def get(self) -> dict[str, Any]:
        return super().get()

    @required_acl('dird.backends.office365.sources.create')
    def post(self) -> dict[str, Any]:
        return super().post()


class MicrosoftItem(SourceItem):
    source_schema = source_schema

    @required_acl('dird.backends.office365.sources.{source_uuid}.delete')
    def delete(self, source_uuid: str) -> tuple[str, int]:
        return super().delete(source_uuid)

    @required_acl('dird.backends.office365.sources.{source_uuid}.read')
    def get(self, source_uuid: str) -> dict[str, Any]:
        return super().get(source_uuid)

    @required_acl('dird.backends.office365.sources.{source_uuid}.update')
    def put(self, source_uuid: str) -> tuple[str, int]:
        return super().put(source_uuid)
