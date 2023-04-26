# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from collections import namedtuple
from flask import request
from xivo.tenant_flask_helpers import Tenant
from wazo_dird import BaseViewPlugin
from wazo_dird.http import AuthResource
from wazo_dird.plugin_helpers.tenant import get_tenant_uuids

logger = logging.getLogger()

DisplayColumn = namedtuple('DisplayColumn', ['title', 'type', 'default', 'field'])


class DisplayAwareResource:
    def build_display(self, profile_config):
        display = profile_config.get('display', {})
        return self._make_display(display)

    @staticmethod
    def _make_display(display):
        columns = display.get('columns')
        if not columns:
            return

        return [
            DisplayColumn(
                column.get('title'),
                column.get('type'),
                column.get('default'),
                column.get('field'),
            )
            for column in columns
        ]


class RaiseStopper:
    def __init__(self, return_on_raise):
        self.return_on_raise = return_on_raise

    def execute(self, function, *args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception:
            logger.exception('An error occured in %s', function.__name__)
        return self.return_on_raise


class BaseService:
    def __init__(self, config, source_manager, controller, *args, **kwargs):
        self._config = config
        self._source_manager = source_manager
        self._controller = controller

    def source_from_profile(self, profile_config):
        service_config = profile_config.get('services', {}).get(self._service_name, {})
        sources = service_config.get('sources', [])

        result = []
        for source in sources:
            source = self._source_manager.get(source['uuid'])
            if not source:
                continue

            result.append(source)

        if not result:
            logger.warning(
                'Cannot find "%s" sources for profile %s',
                self._service_name,
                profile_config['name'],
            )

        return result

    def get_service_config(self, profile_config):
        return profile_config.get('services', {}).get(self._service_name, {})


class _BaseSourceResource(AuthResource):
    def __init__(self, backend, service, auth_config):
        self._service = service
        self._auth_config = auth_config
        self._backend = backend


class SourceList(_BaseSourceResource):
    def get(self):
        list_params = self.list_schema.load(request.args)
        visible_tenants = get_tenant_uuids(recurse=list_params['recurse'])
        sources = self._service.list_(self._backend, visible_tenants, **list_params)
        items = self.source_list_schema.dump(sources)
        filtered = self._service.count(self._backend, visible_tenants, **list_params)
        total = self._service.count(self._backend, visible_tenants)

        return {'total': total, 'filtered': filtered, 'items': items}

    def post(self):
        tenant = Tenant.autodetect()
        args = self.source_schema.load(request.get_json())
        body = self._service.create(self._backend, tenant_uuid=tenant.uuid, **args)
        return self.source_schema.dump(body)


class SourceItem(_BaseSourceResource):
    def delete(self, source_uuid):
        visible_tenants = get_tenant_uuids(recurse=True)
        self._service.delete(self._backend, source_uuid, visible_tenants)
        return '', 204

    def get(self, source_uuid):
        visible_tenants = get_tenant_uuids(recurse=True)
        body = self._service.get(self._backend, source_uuid, visible_tenants)
        return self.source_schema.dump(body)

    def put(self, source_uuid):
        visible_tenants = get_tenant_uuids(recurse=True)
        args = self.source_schema.load(request.get_json())
        self._service.edit(self._backend, source_uuid, visible_tenants, args)
        return '', 204


class BaseBackendView(BaseViewPlugin):
    _required_members = ['backend', 'list_resource', 'item_resource']

    def __init__(self, *args, **kwargs):
        members = [getattr(self, name, None) for name in self._required_members]
        if None in members:
            msg = f'{self.__class__.__name__} should have the following members: {self._required_members}'
            raise Exception(msg)

        super().__init__(*args, **kwargs)

    def load(self, dependencies):
        api = dependencies['api']
        config = dependencies['config']
        service = dependencies['services']['source']

        args = (self.backend, service, config['auth'])

        api.add_resource(
            self.list_resource,
            f'/backends/{self.backend}/sources',
            resource_class_args=args,
        )
        api.add_resource(
            self.item_resource,
            f'/backends/{self.backend}/sources/<source_uuid>',
            resource_class_args=args,
        )
