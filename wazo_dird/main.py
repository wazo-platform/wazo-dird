# Copyright 2014-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import sys

from xivo import xivo_logging
from xivo.config_helper import set_xivo_uuid, UUIDNotFound
from xivo.user_rights import change_user

from wazo_dird.controller import Controller
from wazo_dird.config import load as load_config

logger = logging.getLogger(__name__)


class _PreConfigLogger:
    class FlushableBuffer:
        def __init__(self):
            self._msg = []

        def debug(self, msg, *args, **kwargs):
            self._msg.append((logging.DEBUG, msg, args, kwargs))

        def info(self, msg, *args, **kwargs):
            self._msg.append((logging.INFO, msg, args, kwargs))

        def warning(self, msg, *args, **kwargs):
            self._msg.append((logging.WARNING, msg, args, kwargs))

        def error(self, msg, *args, **kwargs):
            self._msg.append((logging.ERROR, msg, args, kwargs))

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


def main(argv=None):
    argv = argv or sys.argv[1:]
    with _PreConfigLogger() as logger:
        logger.debug('Starting wazo-dird')

        config = load_config(argv)

        xivo_logging.setup_logging(
            config['log_filename'],
            debug=config['debug'],
            log_level=config['log_level'],
        )
    xivo_logging.silence_loggers(
        ['Flask-Cors', 'amqp', 'urllib3', 'stevedore.extension'], logging.WARNING
    )

    if config['user']:
        change_user(config['user'])

    try:
        set_xivo_uuid(config, logger)
    except UUIDNotFound:
        if config['service_discovery']['enabled']:
            raise

    controller = Controller(config)
    controller.run()
