# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from .base import BaseDAO
from .. import Tenant


class TenantCRUD(BaseDAO):
    def delete(self, uuid):
        with self.new_session() as s:
            s.query(Tenant).filter(Tenant.uuid == uuid).delete()

    def list_(self, name=None):
        with self.new_session() as s:
            return [{'uuid': tenant.uuid} for tenant in s.query(Tenant).all()]
