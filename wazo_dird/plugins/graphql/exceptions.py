# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from graphql import GraphQLError


class Unauthorized(GraphQLError):
    def __init__(self):
        super().__init__(message='Unauthorized')


class AuthServerUnreachable(GraphQLError):
    def __init__(self, auth_config):
        message = f'Authentication server {auth_config["host"]}:{auth_config["port"]} unreachable'
        super().__init__(message)


class NoSuchProfileGraphQLError(GraphQLError):
    def __init__(self, profile):
        message = f'No such profile: {profile}'
        super().__init__(message)
