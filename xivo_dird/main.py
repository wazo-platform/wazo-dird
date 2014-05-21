# -*- coding: utf-8 -*-

# Copyright (C) 2014 Avencall
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

import logging

from xivo import daemonize
from xivo_dird import dird_server

logger = logging.getLogger(__name__)

_PID_FILENAME = '/var/run/xivo-dird.pid'


def main():
    _init_logger()
    server = dird_server.DirdServer()
    daemonize.daemonize()
    daemonize.lock_pidfile_or_die(_PID_FILENAME)
    try:
        server.run()
    except Exception as e:
        logger.warning('Unexpected error: %s', e)

    daemonize.unlock_pidfile(_PID_FILENAME)


def _init_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    logger.addHandler(handler)
