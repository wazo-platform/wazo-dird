# -*- coding: utf-8 -*-
#
# Copyright 2016-2017 The Wazo Authors  (see the AUTHORS file)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import logging
import threading

from contextlib import contextmanager

import kombu

from kombu.mixins import ConsumerMixin
from xivo_bus import Marshaler, Publisher

logger = logging.getLogger(__name__)


class Bus(object):

    _bus_url_tpl = 'amqp://{username}:{password}@{host}:{port}//'

    def __init__(self, global_config):
        bus_config = global_config['bus']
        self._enabled = bus_config['enabled']
        if self._enabled:
            self._bus_url = self._bus_url_tpl.format(**bus_config)
            self._marshaler = Marshaler(global_config.get('uuid'))
            self._exchange_name = bus_config['exchange_name']
            self._exchange_type = bus_config['exchange_type']
        self._bus_thread = threading.Thread(target=self._start_consuming)
        self._queues_and_callbacks = []
        self._consumer = None
        self._publisher = None

    def add_consumer(self, queue, callback):
        logger.debug('adding consumer: %s', queue)
        self._queues_and_callbacks.append((queue, callback))

    def publish(self, event, headers):
        logger.debug('publishing: %s', event)
        if self._enabled:
            return self._get_publisher().publish(event, headers)

    @contextmanager
    def start(self):
        if not self._enabled:
            logger.info('bus connection disabled')
            return
        self._bus_thread.start()

    def stop(self):
        logger.info('bus consumer stopping')
        if self._consumer:
            self._consumer.should_stop = True
        if self._bus_thread.isAlive():
            self._bus_thread.join(2.0)
        logger.info('bus consumer stopped')

    def _start_consuming(self):
        logger.info('bus consumer starting')
        logger.debug('Connecting to %s', self._bus_url)
        with kombu.Connection(self._bus_url) as conn:
            self._consumer = _Consumer(conn, self._queues_and_callbacks)
            self._consumer.run()

    def _get_publisher(self):
        if not self._publisher:
            bus_connection = kombu.Connection(self._bus_url)
            bus_exchange = kombu.Exchange(self._exchange_name, type=self._exchange_type)
            producer = kombu.Producer(bus_connection, exchange=bus_exchange, auto_declare=True)
            self._publisher = Publisher(producer, self._marshaler)
        return self._publisher


class _Consumer(ConsumerMixin):

    def __init__(self, connection, queues_and_callbacks):
        self.connection = connection
        self._queues_and_callbacks = queues_and_callbacks

    def get_consumers(self, Consumer, channel):
        return [Consumer(queue, callbacks=[callback])
                for (queue, callback) in self._queues_and_callbacks]
