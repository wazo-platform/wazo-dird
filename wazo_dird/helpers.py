# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
from flask import request
from requests import HTTPError
from xivo.tenant_flask_helpers import Tenant
from xivo_auth_client import Client as AuthClient
from wazo_dird import BaseViewPlugin
from wazo_dird.rest_api import AuthResource

logger = logging.getLogger()


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

    def __init__(self, config, sources, *args, **kwargs):
        self._config = config
        self._sources = sources

    def config_by_profile(self, profile):
        return self._config.get('services', {}).get(self._service_name, {}).get(profile, {})

    def source_by_profile(self, profile):
        sources = self.config_by_profile(profile).get('sources', {})
        result = []

        for name, enabled in sources.items():
            if not enabled or name not in self._sources:
                continue
            result.append(self._sources[name])

        if not result:
            logger.warning('Cannot find "%s" sources for profile %s', self._service_name, profile)

        return result


class _BaseSourceResource(AuthResource):

    def __init__(self, backend, service, auth_config):
        self._service = service
        self._auth_config = auth_config
        self._backend = backend

    def _get_visible_tenants(self, tenant):
        token = request.headers['X-Auth-Token']
        auth_client = AuthClient(**self._auth_config)
        auth_client.set_token(token)

        try:
            visible_tenants = auth_client.tenants.list(tenant_uuid=tenant)['items']
        except HTTPError as e:
            response = getattr(e, 'response', None)
            status_code = getattr(response, 'status_code', None)
            if status_code == 401:
                logger.warning('a user is doing multi-tenant queries without the tenant list ACL')
                return [tenant]
            raise

        return [tenant['uuid'] for tenant in visible_tenants]


class SourceList(_BaseSourceResource):

    def get(self):
        list_params, errors = self.list_schema.load(request.args)
        tenant = Tenant.autodetect()
        if list_params['recurse']:
            visible_tenants = self._get_visible_tenants(tenant.uuid)
        else:
            visible_tenants = [tenant.uuid]

        backends = self._service.list_(self._backend, visible_tenants, **list_params)
        filtered = self._service.count(self._backend, visible_tenants, **list_params)
        total = self._service.count(self._backend, visible_tenants)

        return {
            'total': total,
            'filtered': filtered,
            'items': backends,
        }

    def post(self):
        tenant = Tenant.autodetect()
        args = self.source_schema.load(request.get_json()).data
        body = self._service.create(self._backend, tenant_uuid=tenant.uuid, **args)
        return self.source_schema.dump(body)


class SourceItem(_BaseSourceResource):

    def delete(self, source_uuid):
        tenant = Tenant.autodetect()
        visible_tenants = self._get_visible_tenants(tenant.uuid)
        self._service.delete(self._backend, source_uuid, visible_tenants)
        return '', 204

    def get(self, source_uuid):
        tenant = Tenant.autodetect()
        visible_tenants = self._get_visible_tenants(tenant.uuid)
        body = self._service.get(self._backend, source_uuid, visible_tenants)
        return self.source_schema.dump(body)

    def put(self, source_uuid):
        tenant = Tenant.autodetect()
        visible_tenants = self._get_visible_tenants(tenant.uuid)
        args = self.source_schema.load(request.get_json()).data
        body = self._service.edit(self._backend, source_uuid, visible_tenants, args)
        return self.source_schema.dump(body)


class BaseBackendView(BaseViewPlugin):

    _required_members = [
        'backend',
        'list_resource',
        'item_resource',
    ]

    def __init__(self, *args, **kwargs):
        members = [getattr(self, name, None) for name in self._required_members]
        if None in members:
            msg = '{} should have the following members: {}'.format(
                self.__class__.__name__,
                self._required_members,
            )
            raise Exception(msg)

        super().__init__(*args, **kwargs)

    def load(self, dependencies):
        api = dependencies['api']
        config = dependencies['config']
        service = dependencies['services']['source']

        args = (self.backend, service, config['auth'])

        api.add_resource(
            self.list_resource,
            '/backends/{}/sources'.format(self.backend),
            resource_class_args=args,
        )
        api.add_resource(
            self.item_resource,
            '/backends/{}/sources/<source_uuid>'.format(self.backend),
            resource_class_args=args,
        )
