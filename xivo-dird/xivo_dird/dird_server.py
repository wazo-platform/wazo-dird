# -*- coding: UTF-8 -*-

import logging
from time import sleep

logger = logging.getLogger(__name__)


class DirdServer(object):

    def __init__(self):
        pass

    def run(self):
        logger.info('directory server starting ....')
        while True:
            sleep(1)
        logger.info('directory server stopped .....')
