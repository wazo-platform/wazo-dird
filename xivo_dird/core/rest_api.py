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
from flask import Flask
from flask_restplus.api import Api
from flask_cors import CORS
from werkzeug.contrib.fixers import ProxyFix


VERSION = 0.1

logger = logging.getLogger(__name__)
api = Api(version=VERSION, prefix='/{}'.format(VERSION))


class CoreRestApi(object):

    def __init__(self, config):
        self.config = config
        self.app = Flask('xivo_dird')
        self.app.wsgi_app = ProxyFix(self.app.wsgi_app)
        self.app.secret_key = os.urandom(24)
        self.app.permanent_session_lifetime = timedelta(minutes=5)
        self.load_cors()
        self.api = api
        self.api.init_app(self.app)
        self.namespace = self.api.namespace('directories', description='directories operations')

    def load_cors(self):
        cors_config = dict(self.config.get('cors', {}))
        enabled = cors_config.pop('enabled', False)
        if enabled:
            CORS(self.app, **cors_config)

    def run(self):
        bind_addr = (self.config['listen'], self.config['port'])

        wsgi_app = wsgiserver.WSGIPathInfoDispatcher({'/': self.app})
        server = wsgiserver.CherryPyWSGIServer(bind_addr=bind_addr,
                                               wsgi_app=wsgi_app)

        logger.debug('WSGIServer starting... uid: %s, listen: %s:%s', os.getuid(), bind_addr[0], bind_addr[1])

        try:
            server.start()
        except KeyboardInterrupt:
            server.stop()
