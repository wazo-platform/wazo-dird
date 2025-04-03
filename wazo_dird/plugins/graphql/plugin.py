# Copyright 2020-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

import requests
from graphql_server.flask import GraphQLView
from wazo_auth_client.exceptions import MissingPermissionsTokenException
from xivo.auth_verifier import AuthServerUnreachable, Unauthorized
from xivo.flask.headers import extract_token_id_from_header
from xivo.tenant_helpers import Tenant

from wazo_dird import BaseViewPlugin, http_server

from .exceptions import graphql_error_from_api_exception
from .resolver import Resolver
from .schema import make_schema

if TYPE_CHECKING:
    from wazo_auth_client.client import AuthClient

    from wazo_dird.plugins.source_result import _SourceResult

    from .resolver import ResolveInfo


class AuthorizationMiddleware:
    def __init__(self, auth_config, auth_client: AuthClient) -> None:
        self._auth_config = auth_config
        self._auth_client = auth_client

    def _is_root_query(self, info: ResolveInfo) -> bool:
        return info.path.prev is None

    def _is_authorized(self, info: ResolveInfo, token_id: str) -> bool:
        root_field = info.field_name
        required_acl = f'dird.graphql.{root_field}'
        tenant = Tenant.autodetect(self._auth_client)
        try:
            token_is_valid = self._auth_client.token.check(
                token_id,
                required_acl,
                tenant=tenant.uuid,
            )
            info.context['tenant_uuid'] = tenant.uuid
        except MissingPermissionsTokenException:
            return False
        except requests.RequestException as e:
            host = self._auth_config['host']
            port = self._auth_config['port']
            raise graphql_error_from_api_exception(AuthServerUnreachable(host, port, e))

        return token_is_valid

    def _is_schema_query(self, info: ResolveInfo) -> bool:
        root_field = info.field_name
        return root_field == '__schema'

    def resolve(
        self, next: Callable, root: _SourceResult, info: ResolveInfo, **args: Any
    ):
        if not self._is_root_query(info):
            return next(root, info, **args)

        if self._is_schema_query(info):
            return next(root, info, **args)

        token_id = extract_token_id_from_header()
        if self._is_authorized(info, token_id):
            info.context['token_id'] = token_id
            return next(root, info, **args)

        raise graphql_error_from_api_exception(Unauthorized(token_id))


class GraphQLViewPlugin(BaseViewPlugin):
    def load(self, dependencies):
        app = dependencies['flask_app']

        profile_service = dependencies['services'].get('profile')
        reverse_service = dependencies['services'].get('reverse')
        resolver = Resolver(profile_service, reverse_service)
        schema = make_schema()

        config = dependencies['config']
        auth_client = dependencies['auth_client']
        authorization_middleware = AuthorizationMiddleware(config['auth'], auth_client)

        app.add_url_rule(
            f'/{http_server.VERSION}/graphql',
            view_func=GraphQLView.as_view(
                'graphql',
                schema=schema.graphql_schema,
                middleware=[authorization_middleware],
                context={'resolver': resolver},
            ),
        )
