# Copyright 2016-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from xivo_bus.resources.user.event import UserDeletedEvent

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
    def __init__(self, bus):
        bus.subscribe(UserDeletedEvent.name, self._on_user_deleted_event)

    def _on_user_deleted_event(self, user):
        self._remove_user(user['uuid'])

    # executed in the consumer thread
    def _remove_user(self, user_uuid):
        logger.info('User Deleted event received, removing user %s', user_uuid)
        session = Session()
        database.delete_user(session, user_uuid)
        session.commit()
