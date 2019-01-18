# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

logger = logging.getLogger(__name__)


class WazoBackendService:

    def __init__(self, source_crud):
        self._source_crud = source_crud

    def count(self, visible_tenants, **list_params):
        return self._source_crud.count(visible_tenants, **list_params)

    def create(self, **body):
        return self._source_crud.create(body)

    def delete(self, source_uuid, visible_tenants):
        return self._source_crud.delete(source_uuid, visible_tenants)

    def edit(self, source_uuid, visible_tenants, body):
        return self._source_crud.edit(source_uuid, visible_tenants, body)

    def get(self, source_uuid, visible_tenants):
        return self._source_crud.get(source_uuid, visible_tenants)

    def list_(self, visible_tenants, **list_params):
        return self._source_crud.list_(visible_tenants, **list_params)
