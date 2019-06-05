# Copyright 2016-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os
import time

from datetime import timedelta
from functools import wraps

from requests import HTTPError
from cheroot import wsgi
from flask import Flask
from flask import request
from flask_babel import Babel
from flask_restful import Api
from flask_restful import Resource
from flask_cors import CORS
from wazo_auth_client import Client as AuthClient
from werkzeug.contrib.fixers import ProxyFix
from xivo.auth_verifier import AuthVerifier
from xivo import http_helpers
from xivo import mallow_helpers
from xivo import rest_api_helpers
from xivo.http_helpers import ReverseProxied


VERSION = 0.1
TEMPLATE_FOLDER = 'plugins/templates'

logger = logging.getLogger(__name__)
api = Api(prefix='/{}'.format(VERSION))
api_1 = Api(prefix='/{}'.format(1))
auth_verifier = AuthVerifier()


class CoreRestApi:

    def __init__(self, global_config):
        self.config = global_config['rest_api']
        self.app = Flask('wazo_dird', template_folder=TEMPLATE_FOLDER)
        self.babel = Babel(self.app)
        self.app.config['BABEL_DEFAULT_LOCALE'] = 'en'
        self.app.config['auth'] = global_config['auth']
        AuthResource.auth_config = global_config['auth']

        @self.babel.localeselector
        def get_locale():
            translations = [str(translation) for translation in self.babel.list_translations()]
            return request.accept_languages.best_match(translations)

        http_helpers.add_logger(self.app, logger)
        self.app.after_request(http_helpers.log_request)
        self.app.secret_key = os.urandom(24)
        self.app.permanent_session_lifetime = timedelta(minutes=5)
        self.load_cors()
        self.api = api
        self.api_1 = api_1
        auth_verifier.set_config(global_config['auth'])

    def load_cors(self):
        cors_config = dict(self.config.get('cors', {}))
        enabled = cors_config.pop('enabled', False)
        if enabled:
            CORS(self.app, **cors_config)

    def run(self):
        self.api.init_app(self.app)
        self.api_1.init_app(self.app)

        https_config = self.config['https']

        bind_addr = (https_config['listen'], https_config['port'])

        wsgi_app = ReverseProxied(ProxyFix(wsgi.WSGIPathInfoDispatcher({'/': self.app})))
        server = wsgi.WSGIServer(bind_addr=bind_addr,
                                 wsgi_app=wsgi_app)
        server.ssl_adapter = http_helpers.ssl_adapter(https_config['certificate'],
                                                      https_config['private_key'])
        logger.debug('WSGIServer starting... uid: %s, listen: %s:%s', os.getuid(), bind_addr[0], bind_addr[1])
        for route in http_helpers.list_routes(self.app):
            logger.debug(route)

        try:
            server.start()
        finally:
            server.stop()


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
    method_decorators = [auth_verifier.verify_token] + LegacyErrorCatchingResource.method_decorators


class ErrorCatchingResource(Resource):
    method_decorators = [
        mallow_helpers.handle_validation_exception,
        rest_api_helpers.handle_api_exception,
    ] + Resource.method_decorators


class AuthResource(ErrorCatchingResource):

    method_decorators = [auth_verifier.verify_token] + ErrorCatchingResource.method_decorators

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
                logger.warning('a user is doing multi-tenant queries without the tenant list ACL')
                return [tenant]
            raise

        return [tenant['uuid'] for tenant in visible_tenants]
