# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from itertools import islice
from typing import TYPE_CHECKING, Any

from wazo_dird import BaseServicePlugin, database, exception
from wazo_dird.database.helpers import Session
from wazo_dird.plugin_helpers.sorting import sort_contacts
from wazo_dird.plugin_manager import ServiceDependencies

if TYPE_CHECKING:
    from wazo_dird.controller import Controller

logger = logging.getLogger(__name__)


class ProfileServicePlugin(BaseServicePlugin):
    def load(self, dependencies: ServiceDependencies) -> _ProfileService:
        controller = dependencies['controller']
        return _ProfileService(database.ProfileCRUD(Session), controller)


class _ProfileService:
    def __init__(self, crud: database.ProfileCRUD, controller: Controller) -> None:
        self._profile_crud = crud
        self._controller = controller

    def count(self, visible_tenants: list[str] | None, **list_params: Any) -> int:
        return self._profile_crud.count(visible_tenants, **list_params)

    def create(self, **body: Any) -> dict[str, Any]:
        try:
            return self._profile_crud.create(body)
        except (exception.NoSuchDisplay, exception.NoSuchSource) as e:
            e.status_code = 400
            raise e

    def delete(self, profile_uuid: str, visible_tenants: list[str] | None) -> None:
        self._profile_crud.delete(visible_tenants, profile_uuid)

    def edit(
        self, profile_uuid: str, visible_tenants: list[str] | None, **body: Any
    ) -> None:
        try:
            return self._profile_crud.edit(visible_tenants, profile_uuid, body)
        except (exception.NoSuchDisplay, exception.NoSuchSource) as e:
            e.status_code = 400
            raise e

    def get(
        self, profile_uuid: str, visible_tenants: list[str] | None
    ) -> dict[str, Any]:
        return self._profile_crud.get(visible_tenants, profile_uuid)

    def get_by_name(self, tenant_uuid: str, name: str) -> dict[str, Any]:
        for profile in self._profile_crud.list_([tenant_uuid], name=name):
            return profile

        raise exception.NoSuchProfile(name)

    def get_sources_from_profile_name(
        self, tenant_uuid: str, profile_name: str, **list_params: Any
    ) -> tuple[int, int, list[dict[str, Any]]]:
        try:
            profile = self.get_by_name(tenant_uuid, profile_name)
        except exception.NoSuchProfile as e:
            raise exception.NoSuchProfileAPIException(e.profile)
        sources_by_uuid: dict[str, dict[str, Any]] = {}
        for service in profile.get('services', {}).values():
            for source in service.get('sources', []):
                sources_by_uuid[source['uuid']] = source
        sources = list(sources_by_uuid.values())

        total = len(sources)
        sources = self._filter_sources(sources, **list_params)
        filtered = len(sources)
        sorted_sources = sort_contacts(sources, **list_params)
        paginated_sources = self._paginate(sorted_sources, **list_params)

        return total, filtered, paginated_sources

    def list_(
        self, visible_tenants: list[str] | None, **list_params: Any
    ) -> list[dict[str, Any]]:
        return self._profile_crud.list_(visible_tenants, **list_params)

    def _paginate(
        self,
        sources: list[dict[str, Any]],
        limit: int | None = None,
        offset: int = 0,
        order: str = 'name',
        direction: str = 'asc',
        **ignored: Any,
    ) -> list[dict[str, Any]]:
        if limit is not None:
            limit = offset + limit
            return list(islice(sources, offset, limit))

        return list(islice(sources, offset, None))

    def _filter_sources(
        self,
        sources: list[dict[str, Any]],
        name: str | None = None,
        backend: str | None = None,
        uuid: str | None = None,
        search: str | None = None,
        **ignored: Any,
    ) -> list[dict[str, Any]]:
        filtered_sources = []
        for source in sources:
            if name and source['name'] != name:
                continue
            if backend and source['backend'] != backend:
                continue
            if uuid and source['uuid'] != uuid:
                continue
            if search:
                match = False
                term = search.lower()
                for field in (source['name'].lower(), source['backend'].lower()):
                    if term in field:
                        match = True
                        break
                if not match:
                    continue

            filtered_sources.append(source)
        return filtered_sources

    def _count(
        self,
        sources: list[dict[str, Any]],
        limit: int | None = None,
        offset: int = 0,
        order: str | None = None,
        direction: str | None = None,
        **ignored: Any,
    ) -> int:
        return len(sources)

    def _filtered(
        self,
        sources: list[dict[str, Any]],
        limit: int | None = None,
        offset: int = 0,
        order: str | None = None,
        direction: str | None = None,
        **ignored: Any,
    ) -> int:
        if limit:
            return limit
        else:
            return len(sources) - offset
