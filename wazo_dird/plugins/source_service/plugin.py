# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import logging

from wazo_dird.database.helpers import Session

from wazo_dird import BaseServicePlugin, database
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

    def count(self, backend, visible_tenants, **list_params):
        return self._source_crud.count(backend, visible_tenants, **list_params)

    def create(self, backend, **body):
        return self._source_crud.create(backend, body)

    def delete(self, backend, source_uuid, visible_tenants):
        return self._source_crud.delete(backend, source_uuid, visible_tenants)

    def edit(self, backend, source_uuid, visible_tenants, body):
        result = self._source_crud.edit(backend, source_uuid, visible_tenants, body)
        self._source_manager.invalidate(source_uuid)
        return result

    def get(self, backend, source_uuid, visible_tenants):
        return self._source_crud.get(backend, source_uuid, visible_tenants)

    def get_by_uuid(self, uuid):
        return self._source_crud.get_by_uuid(uuid)

    def list_(self, backend, visible_tenants, **list_params):
        return self._source_crud.list_(backend, visible_tenants, **list_params)
