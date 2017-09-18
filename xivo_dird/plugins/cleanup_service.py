# -*- coding: utf-8 -*-

# Copyright 2016-2017 The Wazo Authors  (see the AUTHORS file)
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

import kombu

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from xivo_bus.marshaler import InvalidMessage, Marshaler
from xivo_bus.resources.user.event import DeleteUserEvent

from xivo_dird import BaseServicePlugin
from xivo_dird import database

logger = logging.getLogger(__name__)


class StorageCleanupServicePlugin(BaseServicePlugin):

    def __init__(self):
        self._service = None

    def load(self, args):
        config = args['config']
        db_uri = config['db_uri']
        bus = args['bus']

        self._service = _StorageCleanupService(db_uri, bus)


class _StorageCleanupService(object):

    _exchange = kombu.Exchange('xivo', type='topic')
    _routing_key = 'config.user.deleted'

    def __init__(self, db_uri, bus):
        self._db_uri = db_uri
        self._Session = scoped_session(sessionmaker())
        engine = create_engine(db_uri)
        self._Session.configure(bind=engine)
        queue = kombu.Queue(exchange=self._exchange,
                            routing_key=self._routing_key,
                            exclusive=True)
        bus.add_consumer(queue, self._on_user_deleted_event)

    # executed in the consumer thread
    def _remove_user(self, user_uuid):
        logger.info('User Deleted event received, removing user %s', user_uuid)
        session = self._Session()
        database.delete_user(session, user_uuid)
        session.commit()

    def _on_user_deleted_event(self, body, message):
        try:
            event = Marshaler.unmarshal_message(body, DeleteUserEvent)
        except (InvalidMessage, KeyError):
            logger.exception('Ignoring the following malformed bus message: %s', body)
        else:
            self._remove_user(event.uuid)
            message.ack()
