# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from itertools import islice
from operator import itemgetter

from wazo_dird import BaseServicePlugin, database, exception
from wazo_dird.database.helpers import Session

logger = logging.getLogger(__name__)


class ProfileServicePlugin(BaseServicePlugin):

    def load(self, dependencies):
        controller = dependencies['controller']
        return _ProfileService(database.ProfileCRUD(Session), controller)


class _ProfileService:

    def __init__(self, crud, controller):
        self._profile_crud = crud
        self._controller = controller

    def count(self, visible_tenants, **list_params):
        return self._profile_crud.count(visible_tenants, **list_params)

    def create(self, **body):
        try:
            return self._profile_crud.create(body)
        except (exception.NoSuchDisplay, exception.NoSuchSource) as e:
            e.status_code = 400
            raise e

    def delete(self, profile_uuid, visible_tenants):
        self._profile_crud.delete(visible_tenants, profile_uuid)

    def edit(self, profile_uuid, visible_tenants, **body):
        try:
            return self._profile_crud.edit(visible_tenants, profile_uuid, body)
        except (exception.NoSuchDisplay, exception.NoSuchSource) as e:
            e.status_code = 400
            raise e

    def get(self, profile_uuid, visible_tenants):
        return self._profile_crud.get(visible_tenants, profile_uuid)

    def get_by_name(self, tenant_uuid, name):
        for profile in self._profile_crud.list_([tenant_uuid], name=name):
            return profile

        raise exception.NoSuchProfile(name)

    def get_sources_from_profile_name(self, tenant_uuid, profile_name, **list_params):
        try:
            profile = self.get_by_name(tenant_uuid, profile_name)
        except exception.NoSuchProfile as e:
            raise exception.NoSuchProfileAPIException(e.profile)
        sources = {}
        for service in profile.get('services', {}).values():
            for source in service.get('sources', []):
                sources[source['uuid']] = source
        sources = list(sources.values())

        total = len(sources)
        sources = self._filter_sources(sources, **list_params)
        filtered = len(sources)
        sources = self._paginate(sources, **list_params)

        return total, filtered, sources

    def list_(self, visible_tenants, **list_params):
        return self._profile_crud.list_(visible_tenants, **list_params)

    def _paginate(self, sources, limit=None, offset=0, order='name', direction='asc', **ignored):
        selected_sources = []

        reverse = direction != 'asc'
        selected_sources = sorted(sources, key=itemgetter(order), reverse=reverse)

        if limit is not None:
            limit = offset + limit
            return list(islice(selected_sources, offset, limit))

        if limit is None:
            return list(islice(selected_sources, offset, None))

    def _filter_sources(self, sources, name=None, backend=None, uuid=None, search=None, **ignored):
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

    def _count(self, sources, limit=None, offset=0, order=None, direction=None, **ignored):
        return len(sources)

    def _filtered(self, sources, limit=None, offset=0, order=None, direction=None, **ignored):
        if limit:
            return limit
        else:
            return len(sources) - offset
