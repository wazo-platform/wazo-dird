# Copyright 2016-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Any

from flask import request
from flask_restful import Resource
from xivo import mallow_helpers, rest_api_helpers
from xivo.flask.auth_verifier import AuthVerifierFlask

auth_verifier = AuthVerifierFlask()


def get_json_body() -> Any:
    # get_json(force=True) raises 400 on a missing/invalid body but returns
    # None for a literal `null` payload; reject that as a 400 so the return is
    # genuinely non-None (Flask's stub types it as Any | None).
    body = request.get_json(force=True)
    if body is None:
        raise rest_api_helpers.APIException(400, 'invalid data', 'invalid-data')
    return body


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
