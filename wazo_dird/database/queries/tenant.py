# Copyright 2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import TypedDict, Union

from wazo_dird.exception import NoSuchTenant

from .. import Tenant
from .base import BaseDAO


class TenantDict(TypedDict, total=False):
    uuid: str
    country: Union[str, None]


class TenantCRUD(BaseDAO):
    def create(self, tenant_uuid: str = None, country: str = None) -> TenantDict:
        return self.create_or_edit(tenant_uuid, {'country': country})

    def create_or_edit(self, tenant_uuid, tenant_body) -> TenantDict:
        with self.new_session() as s:
            try:
                tenant = self._get(s, tenant_uuid)
                tenant.country = tenant_body['country']
            except NoSuchTenant:
                tenant = Tenant(uuid=tenant_uuid, country=tenant_body['country'])
            finally:
                s.add(tenant)
                s.flush()
                return self._from_db_format(tenant)

    def get(self, tenant_uuid: str) -> TenantDict:
        with self.new_session() as s:
            try:
                tenant = self._get(s, tenant_uuid)
            except NoSuchTenant:
                raise
            else:
                return self._from_db_format(tenant)

    def _get(self, session, tenant_uuid) -> Tenant:
        tenant = session.query(Tenant).filter(Tenant.uuid == tenant_uuid).first()
        if not tenant:
            raise NoSuchTenant(tenant_uuid)
        return tenant

    @staticmethod
    def _from_db_format(tenant: Tenant) -> TenantDict:
        return TenantDict(uuid=tenant.uuid, country=tenant.country)

    @staticmethod
    def _to_db_format(tenant: TenantDict) -> Tenant:
        return Tenant(uuid=tenant['uuid'], **{'country': tenant['country']})
