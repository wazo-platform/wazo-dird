# Copyright 2019-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from typing import cast

from wazo_dird import BaseServicePlugin, database
from wazo_dird.database.helpers import Session
from wazo_dird.database.queries.base import Direction
from wazo_dird.database.queries.source import SourceBody, SourceInfo
from wazo_dird.source_manager import SourceManager

logger = logging.getLogger(__name__)


class SourceServicePlugin(BaseServicePlugin):
    def load(self, dependencies) -> _SourceService:
        source_manager = dependencies['source_manager']
        return _SourceService(database.SourceCRUD(Session), source_manager)


class _SourceService:
    def __init__(self, crud: database.SourceCRUD, source_manager: SourceManager):
        self._source_crud = crud
        self._source_manager = source_manager

    def count(self, backend: str, visible_tenants: list[str], **list_params):
        return self._source_crud.count(backend, visible_tenants, **list_params)

    def create(self, backend: str, **body) -> SourceInfo:
        return self._source_crud.create(backend, cast(SourceBody, body))

    def delete(self, backend: str, source_uuid: str, visible_tenants: list[str]):
        return self._source_crud.delete(backend, source_uuid, visible_tenants)

    def edit(
        self, backend: str, source_uuid: str, visible_tenants: list[str], body
    ) -> SourceInfo:
        result = self._source_crud.edit(backend, source_uuid, visible_tenants, body)
        self._source_manager.invalidate(source_uuid)
        return result

    def get(
        self, backend: str, source_uuid: str, visible_tenants: list[str]
    ) -> SourceInfo:
        return self._source_crud.get(backend, source_uuid, visible_tenants)

    def get_by_uuid(self, uuid: str) -> SourceInfo:
        return self._source_crud.get_by_uuid(uuid)

    def list_(
        self,
        backend: str,
        visible_tenants: list[str],
        uuid: str | None = None,
        name: str | None = None,
        search: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
        order: str | None = None,
        direction: Direction | None = None,
        **list_params,
    ):
        return self._source_crud.list_(
            backend,
            visible_tenants,
            uuid=uuid,
            name=name,
            search=search,
            offset=offset,
            limit=limit,
            order=order,
            direction=direction,
            **list_params,
        )
