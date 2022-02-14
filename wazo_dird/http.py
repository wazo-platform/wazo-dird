# Copyright 2016-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import time

from functools import wraps

from requests import HTTPError
from flask import request
from flask_restful import Resource
from wazo_auth_client import Client as AuthClient
from xivo import mallow_helpers, rest_api_helpers
from xivo.auth_verifier import AuthVerifier

logger = logging.getLogger(__name__)

auth_verifier = AuthVerifier()


def handle_api_exception(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
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
        auth_verifier.verify_token
    ] + ErrorCatchingResource.method_decorators

    def get_visible_tenants(self, tenant):
        token = request.headers['X-Auth-Token']
        auth_client = AuthClient(**self.auth_config)
        auth_client.set_token(token)

        try:
            visible_tenants = auth_client.tenants.list(tenant_uuid=tenant)['items']
        except HTTPError as e:
            response = getattr(e, 'response', None)
            status_code = getattr(response, 'status_code', None)
            if status_code == 401:
                logger.warning(
                    'a user is doing multi-tenant queries without the tenant list ACL'
                )
                return [tenant]
            raise

        return [tenant['uuid'] for tenant in visible_tenants]
