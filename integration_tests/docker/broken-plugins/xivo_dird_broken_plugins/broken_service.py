# Copyright 2020-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import kombu
from xivo_bus.resources.common.event import BaseEvent


class PongEvent(BaseEvent):

    name = 'dird_pong'
    routing_key_fmt = 'dird.test'

    _body = {'payload': 'pong'}


class BrokenBusPlugin:

    _QUEUE = kombu.Queue(
        exchange=kombu.Exchange('xivo', type='topic'),
        routing_key='dird.test',
        exclusive=True,
    )

    def load(self, dependencies):
        import logging

        logger = logging.getLogger(__name__)

        logger.critical('LOAD')
        self.bus = dependencies['bus']
        self.bus.add_consumer(self._QUEUE, self.on_dird_test_message)

    def on_dird_test_message(self, body, message):
        if body['name'] == 'dird_ping':
            self.bus.publish(PongEvent(), headers={})
        elif body['name'] == 'crash_ping':
            raise Exception('Crash message received')
