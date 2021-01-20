# Copyright 2016-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

import kombu

from xivo_bus.marshaler import InvalidMessage, Marshaler
from xivo_bus.resources.user.event import DeleteUserEvent

from wazo_dird import BaseServicePlugin
from wazo_dird import database
from wazo_dird.database.helpers import Session

logger = logging.getLogger(__name__)


class StorageCleanupServicePlugin(BaseServicePlugin):
    def __init__(self):
        self._service = None

    def load(self, args):
        bus = args['bus']

        self._service = _StorageCleanupService(bus)


class _StorageCleanupService:

    _exchange = kombu.Exchange('xivo', type='topic')
    _routing_key = 'config.user.deleted'

    def __init__(self, bus):
        queue = kombu.Queue(
            exchange=self._exchange, routing_key=self._routing_key, exclusive=True
        )
        bus.add_consumer(queue, self._on_user_deleted_event)

    # executed in the consumer thread
    def _remove_user(self, user_uuid):
        logger.info('User Deleted event received, removing user %s', user_uuid)
        session = Session()
        database.delete_user(session, user_uuid)
        session.commit()

    def _on_user_deleted_event(self, body, message):
        try:
            event = Marshaler.unmarshal_message(body, DeleteUserEvent)
        except (InvalidMessage, KeyError):
            logger.exception('Ignoring the following malformed bus message: %s', body)
        else:
            self._remove_user(event.uuid)
