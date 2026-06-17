# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from typing import Any

from wazo_dird import BaseServicePlugin, database
from wazo_dird.database.helpers import Session
from wazo_dird.plugin_manager import ServiceDependencies

logger = logging.getLogger(__name__)


class DisplayServicePlugin(BaseServicePlugin):
    def load(self, dependencies: ServiceDependencies) -> _DisplayService:
        return _DisplayService(database.DisplayCRUD(Session))


class _DisplayService:
    def __init__(self, crud: database.DisplayCRUD) -> None:
        self._display_crud = crud

    def count(self, visible_tenants: list[str] | None, **list_params: Any) -> int:
        return self._display_crud.count(visible_tenants, **list_params)

    def create(self, **body: Any) -> dict[str, Any]:
        return self._display_crud.create(**body)

    def delete(self, display_uuid: str, visible_tenants: list[str] | None) -> None:
        return self._display_crud.delete(visible_tenants, display_uuid)

    def edit(
        self, display_uuid: str, visible_tenants: list[str] | None, **body: Any
    ) -> None:
        return self._display_crud.edit(visible_tenants, display_uuid, **body)

    def get(
        self, display_uuid: str, visible_tenants: list[str] | None
    ) -> dict[str, Any]:
        return self._display_crud.get(visible_tenants, display_uuid)

    def list_(
        self, visible_tenants: list[str] | None, **list_params: Any
    ) -> list[dict[str, Any]]:
        return self._display_crud.list_(visible_tenants, **list_params)
