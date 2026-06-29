# Copyright 2016-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, Literal, TypeVar, cast, overload

from flask import request
from flask_restful import Resource
from xivo import mallow_helpers, rest_api_helpers
from xivo.flask.auth_verifier import AuthVerifierFlask

R = TypeVar('R')

logger = logging.getLogger(__name__)

auth_verifier = AuthVerifierFlask()


@overload
def get_json_body(many: Literal[False] = False) -> dict[str, Any]:
    ...


@overload
def get_json_body(many: Literal[True]) -> list[dict[str, Any]]:
    ...


def get_json_body(many: bool = False) -> dict[str, Any] | list[dict[str, Any]]:
    # get_json(force=True) raises on a missing/invalid body, so it never
    # returns None at runtime; Flask's stub types it as Any | None regardless.
    # `many` mirrors marshmallow: a JSON array body deserializes to a list.
    body = request.get_json(force=True)
    if many:
        return cast('list[dict[str, Any]]', body)
    return cast('dict[str, Any]', body)


def handle_api_exception(
    func: Callable[..., R],
) -> Callable[..., R | tuple[dict[str, Any], int]]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> R | tuple[dict[str, Any], int]:
        try:
            return func(*args, **kwargs)
        except rest_api_helpers.APIException as error:
            response = {
                'reason': [error.message],
                'timestamp': time.time(),
                'status_code': error.status_code,
            }
            logger.error('%s: %s', error.message, error.details)
            return response, error.status_code

    return wrapper


class LegacyErrorCatchingResource(Resource):
    method_decorators = [handle_api_exception] + Resource.method_decorators


class LegacyAuthResource(LegacyErrorCatchingResource):
    method_decorators = [
        auth_verifier.verify_token
    ] + LegacyErrorCatchingResource.method_decorators


class ErrorCatchingResource(Resource):
    method_decorators = [
        mallow_helpers.handle_validation_exception,
        rest_api_helpers.handle_api_exception,
    ] + Resource.method_decorators


class AuthResource(ErrorCatchingResource):
    method_decorators = [
        auth_verifier.verify_tenant,
        auth_verifier.verify_token,
    ] + ErrorCatchingResource.method_decorators
