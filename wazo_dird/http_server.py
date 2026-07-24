# Copyright 2016-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
import os
from datetime import timedelta

from flask import Flask
from flask_cors import CORS
from flask_restful import Api
from werkzeug.middleware.proxy_fix import ProxyFix
from xivo import http_helpers, wsgi
from xivo.http_helpers import ReverseProxied

from .config import Config, RestAPIConfig
from .http import (
    AuthResource,
    ErrorCatchingResource,
    LegacyAuthResource,
    LegacyErrorCatchingResource,
)

# Compatibility for old plugins < 22.03
__all__ = [
    'LegacyErrorCatchingResource',
    'LegacyAuthResource',
    'ErrorCatchingResource',
    'AuthResource',
]

logger = logging.getLogger(__name__)

VERSION = 0.1
TEMPLATE_FOLDER = 'plugins/templates'

app = Flask('wazo-dird')
api = Api(app, prefix=f'/{VERSION}')


class CoreRestApi:
    def __init__(self, global_config: Config) -> None:
        self.config: RestAPIConfig = global_config['rest_api']
        app.config['auth'] = global_config['auth']
        http_helpers.add_logger(app, logger)
        app.before_request(http_helpers.log_before_request)
        app.after_request(http_helpers.log_request)
        app.secret_key = os.urandom(24)
        app.permanent_session_lifetime = timedelta(minutes=5)
        app.config.update(global_config)
        self.load_cors()
        self.server: wsgi.DynamicWSGIServer | None = None
        self.app = app
        self.api = api

    def load_cors(self) -> None:
        cors_config = dict(self.config.get('cors', {}))
        enabled = cors_config.pop('enabled', False)
        if enabled:
            CORS(app, **cors_config)

    def run(self) -> None:
        bind_addr = (self.config['listen'], self.config['port'])

        wsgi_app = ReverseProxied(ProxyFix(wsgi.WSGIPathInfoDispatcher({'/': app})))
        self.server = wsgi.DynamicWSGIServer(
            bind_addr=bind_addr,
            wsgi_app=wsgi_app,
            numthreads=self.config['min_threads'],
            max=self.config['max_threads'],
        )
        if self.config['certificate'] and self.config['private_key']:
            logger.warning(
                'Using service SSL configuration is deprecated. Please use NGINX instead.'
            )
            self.server.ssl_adapter = http_helpers.ssl_adapter(
                self.config['certificate'], self.config['private_key']
            )

        logger.debug(
            'WSGIServer starting... uid: %s, listen: %s:%s',
            os.getuid(),
            bind_addr[0],
            bind_addr[1],
        )
        for route in http_helpers.list_routes(app):
            logger.debug(route)

        self.server.start()

    def stop(self) -> None:
        if self.server:
            self.server.stop()
