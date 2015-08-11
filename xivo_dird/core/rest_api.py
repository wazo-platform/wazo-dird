# -*- coding: utf-8 -*-

# Copyright (C) 2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

from datetime import timedelta

import logging
import os

from cherrypy import wsgiserver
from cherrypy.wsgiserver.ssl_builtin import BuiltinSSLAdapter
from flask import Flask
from flask_restful import Api
from flask_cors import CORS
from werkzeug.contrib.fixers import ProxyFix
from xivo import http_helpers

from xivo_dird.swagger.resource import SwaggerResource


VERSION = 0.1

logger = logging.getLogger(__name__)
api = Api(prefix='/{}'.format(VERSION))


class CoreRestApi(object):

    def __init__(self, config):
        self.config = config
        self.app = Flask('xivo_dird')
        http_helpers.add_logger(self.app, logger)
        self.app.after_request(http_helpers.log_request)
        self.app.wsgi_app = ProxyFix(self.app.wsgi_app)
        self.app.secret_key = os.urandom(24)
        self.app.permanent_session_lifetime = timedelta(minutes=5)
        self.load_cors()
        self.api = api
        SwaggerResource.add_resource(api)

    def load_cors(self):
        cors_config = dict(self.config.get('cors', {}))
        enabled = cors_config.pop('enabled', False)
        if enabled:
            CORS(self.app, **cors_config)

    def run(self):
        self.api.init_app(self.app)

        bind_addr = (self.config['listen'], self.config['port'])

        _check_file_readable(self.config['certificate'])
        _check_file_readable(self.config['private_key'])
        ssl_adapter = BuiltinSSLAdapter(self.config['certificate'],
                                        self.config['private_key'])
        wsgi_app = wsgiserver.WSGIPathInfoDispatcher({'/': self.app})
        server = wsgiserver.CherryPyWSGIServer(bind_addr=bind_addr,
                                               wsgi_app=wsgi_app)
        server.ssl_adapter = ssl_adapter

        logger.debug('WSGIServer starting... uid: %s, listen: %s:%s', os.getuid(), bind_addr[0], bind_addr[1])

        list_routes(self.app)

        try:
            server.start()
        except KeyboardInterrupt:
            server.stop()


def _check_file_readable(file_path):
    with open(file_path, 'r'):
        pass


def list_routes(app):
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = "{:50s} {:20s} {}".format(rule.endpoint, methods, rule)
        output.append(line)

    for line in sorted(output):
        logger.debug(line)
