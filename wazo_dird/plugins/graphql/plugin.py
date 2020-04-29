# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import requests

from flask_graphql import GraphQLView
from graphql import GraphQLError
from wazo_dird import BaseViewPlugin
from wazo_dird import rest_api
from xivo import auth_verifier

from .resolver import Resolver
from .schema import make_schema


class Unauthorized(GraphQLError):
    def __init__(self):
        super().__init__(message='Unauthorized')


class AuthServerUnreachable(GraphQLError):
    def __init__(self, auth_config):
        message = f'Authentication server {auth_config["host"]}:{auth_config["port"]} unreachable'
        super().__init__(message)


class AuthorizationMiddleware:
    def __init__(self, auth_config, auth_client):
        self._auth_config = auth_config
        self._auth_client = auth_client

    def _is_root_query(self, info):
        return 'prev' not in info.path

    def _is_authorized(self, info):
        root_field = info.field_name
        required_acl = f'dird.graphql.{root_field}'
        token_id = auth_verifier.extract_token_id_from_header()
        try:
            token_is_valid = self._auth_client.token.is_valid(token_id, required_acl)
        except requests.RequestException:
            raise AuthServerUnreachable(self._auth_config)

        return token_is_valid

    def resolve(self, next, root, info, **args):
        if self._is_root_query(info) and not self._is_authorized(info):
            raise Unauthorized()

        return next(root, info, **args)


class GraphQLViewPlugin(BaseViewPlugin):
    def load(self, dependencies):
        app = dependencies['flask_app']
        config = dependencies['config']
        resolver = Resolver()
        schema = make_schema(resolver)
        auth_client = dependencies['auth_client']
        authorization_middleware = AuthorizationMiddleware(config['auth'], auth_client)

        app.add_url_rule(
            '/{version}/graphql'.format(version=rest_api.VERSION),
            view_func=GraphQLView.as_view(
                'graphql',
                schema=schema,
                middleware=[authorization_middleware],
                # get_context: source: https://github.com/graphql-python/flask-graphql/issues/52#issuecomment-412773200
                get_context=dict,
            ),
        )
