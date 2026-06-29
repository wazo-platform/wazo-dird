# Copyright 2016-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from typing import Any

from wazo_bus.resources.user.event import UserDeletedEvent

from wazo_dird import BaseServicePlugin, database
from wazo_dird.bus import CoreBus
from wazo_dird.database.helpers import Session
from wazo_dird.plugin_manager import ServiceDependencies

logger = logging.getLogger(__name__)


class StorageCleanupServicePlugin(BaseServicePlugin):
    def __init__(self) -> None:
        self._service: _StorageCleanupService | None = None

    def load(self, args: ServiceDependencies) -> None:
        bus = args['bus']

        self._service = _StorageCleanupService(bus)


class _StorageCleanupService:
    def __init__(self, bus: CoreBus) -> None:
        bus.subscribe(UserDeletedEvent.name, self._on_user_deleted_event)

    def _on_user_deleted_event(self, user: dict[str, Any]) -> None:
        self._remove_user(user['uuid'])

    # executed in the consumer thread
    def _remove_user(self, user_uuid: str) -> None:
        logger.info('User Deleted event received, removing user %s', user_uuid)
        session = Session()
        database.delete_user(session, user_uuid)
        session.commit()
