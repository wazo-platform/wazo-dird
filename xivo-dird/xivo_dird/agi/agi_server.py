# -*- coding: UTF-8 -*-

# Copyright (C) 2012  Avencall
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA..

from __future__ import absolute_import

import logging
import SocketServer
from xivo_dird.agi.agi_request_handler import AgiRequestHandler

LISTEN_ADDRESS_DEFAULT = "127.0.0.1"
LISTEN_PORT_DEFAULT = 5002


logger = logging.getLogger(__name__)


class AgiServer(SocketServer.ThreadingTCPServer):

    def __init__(self):
        self._listen_address = LISTEN_ADDRESS_DEFAULT
        self._listen_port = LISTEN_PORT_DEFAULT

    def run(self):
        logger.info('running server on address %s port %s' % (self._listen_address, self._listen_port))

        SocketServer.ThreadingTCPServer.__init__(self, (self._listen_address, self._listen_port),
                                                           AgiRequestHandler)

        self.serve_forever()
