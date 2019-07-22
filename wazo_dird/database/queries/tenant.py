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
            if name is not None:
                filter_ = Tenant.name == name
            else:
                filter_ = True

            result = []
            for tenant in s.query(Tenant).filter(filter_).all():
                result.append({'uuid': tenant.uuid, 'name': tenant.name})
            return result
