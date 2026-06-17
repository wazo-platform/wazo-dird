# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import time
from typing import Any

from graphql import GraphQLError
from xivo.rest_api_helpers import APIException


class Unauthorized(GraphQLError):  # type: ignore[misc]
    def __init__(self) -> None:
        super().__init__(message='Unauthorized')


class AuthServerUnreachable(GraphQLError):  # type: ignore[misc]
    def __init__(self, auth_config: dict[str, Any]) -> None:
        message = f'Authentication server {auth_config["host"]}:{auth_config["port"]} unreachable'
        super().__init__(message)


def graphql_error_from_api_exception(e: APIException) -> GraphQLError:
    extensions: dict[str, Any] = {
        'error_id': e.id_,
        'details': e.details or {},
        'timestamp': time.time(),
    }
    if e.resource:
        extensions['resource'] = e.resource
    return GraphQLError(e.message, extensions=extensions)
