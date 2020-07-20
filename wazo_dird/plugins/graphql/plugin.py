# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import requests

from flask_graphql import GraphQLView
from wazo_dird import BaseViewPlugin
from wazo_dird import rest_api
from xivo.auth_verifier import (
    AuthServerUnreachable,
    Unauthorized,
    extract_token_id_from_header,
)

from .exceptions import graphql_error_from_api_exception
from .resolver import Resolver
from .schema import make_schema


class AuthorizationMiddleware:
    def __init__(self, auth_config, auth_client):
        self._auth_config = auth_config
        self._auth_client = auth_client

    def _is_root_query(self, info):
        return len(info.path) == 1

    def _is_authorized(self, info, token_id):
        root_field = info.field_name
        required_acl = f'dird.graphql.{root_field}'
        try:
            token_is_valid = self._auth_client.token.is_valid(token_id, required_acl)
        except requests.RequestException as e:
            host = self._auth_config['host']
            port = self._auth_config['port']
            raise graphql_error_from_api_exception(AuthServerUnreachable(host, port, e))

        return token_is_valid

    def _is_schema_query(self, info):
        root_field = info.field_name
        return root_field == '__schema'

    def resolve(self, next, root, info, **args):
        if not self._is_root_query(info):
            return next(root, info, **args)

        if self._is_schema_query(info):
            return next(root, info, **args)

        token_id = extract_token_id_from_header()
        if self._is_authorized(info, token_id):
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
            '/{version}/graphql'.format(version=rest_api.VERSION),
            view_func=GraphQLView.as_view(
                'graphql',
                schema=schema,
                middleware=[authorization_middleware],
                # get_context: source: https://github.com/graphql-python/flask-graphql/issues/52#issuecomment-412773200
                get_context=lambda: {'resolver': resolver},
            ),
        )
