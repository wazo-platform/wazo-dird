# Copyright 2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import TypedDict

from wazo_dird.exception import NoSuchTenant

from .. import Tenant
from .base import BaseDAO


class TenantCRUD(BaseDAO):
    def create(self, tenant_uuid: str = None, country: str = None) -> None:
        self.create_or_edit(tenant_uuid, {'country': country})

    def create_or_edit(self, tenant_uuid, tenant_body) -> Tenant:
        with self.new_session() as s:
            try:
                tenant = self.get(tenant_uuid)
            except NoSuchTenant:
                tenant = Tenant(uuid=tenant_uuid, **tenant_body)
            else:
                s.add(tenant)
                s.flush()
                return tenant

    def get(self, tenant_uuid: str) -> Tenant:
        with self.new_session() as s:
            tenant = s.query(Tenant).filter(Tenant.uuid == tenant_uuid).scalar()
        if not tenant:
            raise NoSuchTenant(tenant_uuid)
        return tenant
