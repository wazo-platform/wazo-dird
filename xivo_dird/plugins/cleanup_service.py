# -*- coding: utf-8 -*-

# Copyright (C) 2016 Avencall
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

import kombu
import logging
import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from kombu.mixins import ConsumerMixin
from xivo_bus.marshaler import InvalidMessage, Marshaler
from xivo_bus.resources.user.event import DeleteUserEvent

from xivo_dird import BaseServicePlugin
from xivo_dird import database

logger = logging.getLogger(__name__)


class StorageCleanupServicePlugin(BaseServicePlugin):

    _bus_url_tpl = 'amqp://{username}:{password}@{host}:{port}//'

    def __init__(self):
        self._service = None

    def load(self, args):
        config = args['config']
        db_uri = config['db_uri']
        bus_config = config['bus']
        bus_url = self._bus_url_tpl.format(**bus_config)

        self._service = _StorageCleanupService(db_uri, bus_url)

    def unload(self):
        if self._service:
            self._service.stop()


class _StorageCleanupService(object):

    def __init__(self, db_uri, bus_url):
        self._db_uri = db_uri
        self._bus_url = bus_url
        self._bus_thread = threading.Thread(target=self._start_consuming)
        self._bus_thread.start()
        self._consumer = None
        self._Session = scoped_session(sessionmaker())
        engine = create_engine(db_uri)
        self._Session.configure(bind=engine)

    def stop(self):
        if self._consumer:
            self._consumer.should_stop = True
            self._bus_thread.join()

    def _start_consuming(self):
        logger.debug('Connecting to %s', self._bus_url)
        with kombu.Connection(self._bus_url) as conn:
            self._consumer = _UserDeletedConsumer(conn, self)
            self._consumer.run()

    # executed in the consumer thread
    def remove_user(self, user_uuid):
        logger.info('User Deleted event received, removing user %s', user_uuid)
        session = self._Session()
        database.delete_user(session, user_uuid)
        session.commit()


class _UserDeletedConsumer(ConsumerMixin):

    _exchange = kombu.Exchange('xivo', type='topic')
    _routing_key = 'config.user.deleted'

    def __init__(self, connection, service):
        self.connection = connection
        self._queue = kombu.Queue(exchange=self._exchange, routing_key=self._routing_key, exclusive=True)
        self._service = service

    def get_consumers(self, Consumer, channel):
        return [Consumer(self._queue, callbacks=[self.on_message])]

    def on_message(self, body, message):
        try:
            event = Marshaler.unmarshal_message(body, DeleteUserEvent)
        except (InvalidMessage, KeyError):
            logger.exception('Ignoring the following malformed bus message: %s', body)
        else:
            self._service.remove_user(event.uuid)
            message.ack()
