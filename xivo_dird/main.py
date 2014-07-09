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

import argparse
import logging

from flup.server.fcgi import WSGIServer

from xivo.daemonize import daemon_context
from xivo.xivo_logging import setup_logging
from xivo_dird import dird_server

logger = logging.getLogger(__name__)

_DAEMONNAME = 'xivo-dird'
_LOG_FILENAME = '/var/log/{}.log'.format(_DAEMONNAME)
_PID_FILENAME = '/var/run/{}.pid'.format(_DAEMONNAME)


def main():
    parsed_args = _parse_args()

    setup_logging(_LOG_FILENAME, parsed_args.foreground, parsed_args.debug)

    if parsed_args.foreground:
        _run(parsed_args.debug)
    else:
        with daemon_context(_PID_FILENAME):
            _run(parsed_args.debug)


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f',
                        '--foreground',
                        action='store_true',
                        default=False,
                        help="Foreground, don't daemonize. Default: %(default)s")
    parser.add_argument('-d',
                        '--debug',
                        action='store_true',
                        default=False,
                        help="Enable debug messages. Default: %(default)s")
    return parser.parse_args()


def _run(debug=False):
    WSGIServer(dird_server.app,
               bindAddress='/var/www/{}.sock'.format(_DAEMONNAME),
               multithreaded=False,
               multiprocess=True,
               debug=debug).run()
