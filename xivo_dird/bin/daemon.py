# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2015 Avencall
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
import sys

from xivo.daemonize import pidfile_context
from xivo.user_rights import change_user
from xivo import xivo_logging
from xivo_dird.controller import Controller
from xivo_dird.config import load as load_config

logger = logging.getLogger(__name__)


class _PreConfigLogger(object):

    class FlushableBuffer(object):

        def __init__(self):
            self._msg = []

        def info(self, msg, *args, **kwargs):
            self._msg.append((logging.INFO, msg, args, kwargs))

        def debug(self, msg, *args, **kwargs):
            self._msg.append((logging.DEBUG, msg, args, kwargs))

        def warning(self, msg, *args, **kwargs):
            self._msg.append((logging.WARNING, msg, args, kwargs))

        def critical(self, msg, *args, **kwargs):
            self._msg.append((logging.CRITICAL, msg, args, kwargs))

        def flush(self):
            for level, msg, args, kwargs in self._msg:
                logger.log(level, msg, *args, **kwargs)

    def __enter__(self):
        self._logger = self.FlushableBuffer()
        return self._logger

    def __exit__(self, _type, _value, _tb):
        self._logger.flush()


def main(argv):
    with _PreConfigLogger() as logger:
        logger.debug('Starting xivo-dird')

        config = load_config(logger, argv)

        xivo_logging.setup_logging(config['log_filename'], config['foreground'],
                                   config['debug'], config['log_level'])

    xivo_logging.silence_loggers(['Flask-Cors', 'urllib3'], logging.WARNING)
    if config['user']:
        change_user(config['user'])

    controller = Controller(config)

    with pidfile_context(config['pid_filename'], config['foreground']):
        controller.run()


if __name__ == '__main__':
    main(sys.argv[1:])
