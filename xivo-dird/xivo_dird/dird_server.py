# -*- coding: UTF-8 -*-

from __future__ import absolute_import

import logging
from xivo_dird.agi.agi_server import AgiServer

logger = logging.getLogger(__name__)


class DirdServer(object):

    def __init__(self):
        pass

    def run(self):
        logger.info('directory server starting ....')
        agi_server = AgiServer()
        agi_server.run()
        logger.info('directory server stopped .....')
