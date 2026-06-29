# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from flask import request
from xivo.tenant_flask_helpers import Tenant, token

from wazo_dird.auth import required_acl
from wazo_dird.helpers import AuthConfig, SourceItem, SourceList
from wazo_dird.http import AuthResource

from .exceptions import GoogleTokenNotFoundException
from .schemas import contact_list_schema, list_schema, source_list_schema, source_schema
from .services import GoogleService, get_google_access_token

if TYPE_CHECKING:
    from wazo_dird.plugins.source_service.plugin import _SourceService

logger = logging.getLogger(__name__)


class GoogleContactList(AuthResource):
    BACKEND = 'google'

    def __init__(
        self,
        auth_config: AuthConfig,
        config: dict[str, Any],
        source_service: _SourceService,
    ) -> None:
        self.auth_config = auth_config
        self.config = config
        self.source_service = source_service
        self.google = GoogleService()

    @required_acl('dird.backends.google.sources.{source_uuid}.contacts.read')
    def get(self, source_uuid: str) -> tuple[dict[str, Any], int]:
        user_uuid = token.user_uuid
        token_from_request = request.headers.get('X-Auth-Token')
        tenant = Tenant.autodetect()
        list_params = contact_list_schema.load(request.args)

        source = self.source_service.get(self.BACKEND, source_uuid, [tenant.uuid])
        # The google source schema adds an "auth" field that is not part of the
        # base SourceInfo TypedDict.
        source_auth: dict[str, Any] = cast(dict[str, Any], source)['auth']
        if user_uuid is None or token_from_request is None:
            raise GoogleTokenNotFoundException(user_uuid or '')
        google_token = get_google_access_token(
            user_uuid, token_from_request, **source_auth
        )
        if google_token is None:
            raise GoogleTokenNotFoundException(user_uuid)

        contacts, total = self.google.get_contacts(google_token, **list_params)

        return {'filtered': total, 'items': contacts, 'total': total}, 200


class GoogleList(SourceList):
    list_schema = list_schema
    source_schema = source_schema
    source_list_schema = source_list_schema

    @required_acl('dird.backends.google.sources.read')
    def get(self) -> dict[str, Any]:
        return super().get()

    @required_acl('dird.backends.google.sources.create')
    def post(self) -> dict[str, Any]:
        return super().post()


class GoogleItem(SourceItem):
    source_schema = source_schema

    @required_acl('dird.backends.google.sources.{source_uuid}.delete')
    def delete(self, source_uuid: str) -> tuple[str, int]:
        return super().delete(source_uuid)

    @required_acl('dird.backends.google.sources.{source_uuid}.read')
    def get(self, source_uuid: str) -> dict[str, Any]:
        return super().get(source_uuid)

    @required_acl('dird.backends.google.sources.{source_uuid}.update')
    def put(self, source_uuid: str) -> tuple[str, int]:
        return super().put(source_uuid)
