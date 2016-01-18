# -*- coding: utf-8 -*-

# Copyright (C) 2016 Avencall
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
from flask import Flask
from flask import request
from flask.ext.babel import Babel
from flask_restful import Api
from flask_cors import CORS
from xivo import http_helpers

from xivo_dird.swagger.resource import SwaggerResource


VERSION = 0.1
TEMPLATE_FOLDER = 'plugins/templates'

logger = logging.getLogger(__name__)
api = Api(prefix='/{}'.format(VERSION))


class CoreRestApi(object):

    def __init__(self, config):
        self.config = config
        self.app = Flask('xivo_dird', template_folder=TEMPLATE_FOLDER)
        self.babel = Babel(self.app)
        self.app.config['BABEL_DEFAULT_LOCALE'] = 'en'

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
        SwaggerResource.add_resource(api)

    def load_cors(self):
        cors_config = dict(self.config.get('cors', {}))
        enabled = cors_config.pop('enabled', False)
        if enabled:
            CORS(self.app, **cors_config)

    def run(self):
        self.api.init_app(self.app)

        https_config = self.config['https']

        bind_addr = (https_config['listen'], https_config['port'])

        wsgi_app = wsgiserver.WSGIPathInfoDispatcher({'/': self.app})
        server = wsgiserver.CherryPyWSGIServer(bind_addr=bind_addr,
                                               wsgi_app=wsgi_app)
        server.ssl_adapter = http_helpers.ssl_adapter(https_config['certificate'],
                                                      https_config['private_key'],
                                                      https_config.get('ciphers'))
        logger.debug('WSGIServer starting... uid: %s, listen: %s:%s', os.getuid(), bind_addr[0], bind_addr[1])
        for route in http_helpers.list_routes(self.app):
            logger.debug(route)

        try:
            server.start()
        except KeyboardInterrupt:
            server.stop()
