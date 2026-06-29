# Copyright 2015-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from collections import namedtuple
from collections.abc import Callable
from typing import Any, Generic, TypedDict, TypeVar

from flask import request
from flask_restful import Api
from xivo.tenant_flask_helpers import Tenant

from wazo_dird import BaseSourcePlugin
from wazo_dird.controller import Controller
from wazo_dird.database.queries.source import SourceBody, SourceInfo
from wazo_dird.exception import InvalidSourceConfigAPIError, InvalidSourceConfigError
from wazo_dird.http import AuthResource
from wazo_dird.plugin_helpers.tenant import get_tenant_uuids
from wazo_dird.plugins.base_plugins import BaseViewPlugin, SourceConfig
from wazo_dird.plugins.source_service.plugin import _SourceService
from wazo_dird.source_manager import SourceManager

T = TypeVar('T')

logger = logging.getLogger()

DisplayColumn = namedtuple('DisplayColumn', ['title', 'type', 'default', 'field'])


class DisplayAwareResource:
    def build_display(
        self, profile_config: dict[str, Any]
    ) -> list[DisplayColumn] | None:
        display = profile_config.get('display', {})
        return self._make_display(display)

    @staticmethod
    def _make_display(display: dict[str, Any]) -> list[DisplayColumn] | None:
        columns = display.get('columns')
        if not columns:
            return None

        return [
            DisplayColumn(
                column.get('title'),
                column.get('type'),
                column.get('default'),
                column.get('field'),
            )
            for column in columns
        ]


class RaiseStopper(Generic[T]):
    def __init__(self, return_on_raise: T):
        self.return_on_raise = return_on_raise

    def execute(self, function: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        try:
            return function(*args, **kwargs)
        except Exception:
            logger.exception('An error occured in %s', function.__name__)
        return self.return_on_raise


class ServiceConfigOptions(TypedDict, total=False):
    timeout: float


class ServiceConfig(TypedDict, total=False):
    sources: list[SourceConfig]
    options: ServiceConfigOptions


class ProfileConfig(TypedDict, total=False):
    name: str
    services: dict[str, ServiceConfig]


class BaseService:
    _service_name: str

    def __init__(
        self,
        config: dict[str, Any],
        source_manager: SourceManager,
        controller: Controller,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self._config = config
        self._source_manager = source_manager
        self._controller = controller

    def source_from_profile(
        self, profile_config: ProfileConfig
    ) -> list[BaseSourcePlugin]:
        service_config = profile_config.get('services', {}).get(self._service_name, {})
        source_configs = service_config.get('sources', [])

        result = []
        for source_config in source_configs:
            source = self._source_manager.get(source_config['uuid'])
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

    def get_service_config(self, profile_config: ProfileConfig) -> ServiceConfig:
        return profile_config.get('services', {}).get(self._service_name, {})


class AuthConfig(TypedDict):
    host: str
    backend: str
    username: str
    password: str


class _BaseSourceResource(AuthResource):
    def __init__(self, backend: str, service: _SourceService, auth_config: AuthConfig):
        self._service = service
        self._auth_config = auth_config
        self._backend = backend


class SourceList(_BaseSourceResource):
    def get(self) -> dict[str, Any]:
        list_params = self.list_schema.load(request.args)
        visible_tenants = get_tenant_uuids(recurse=list_params['recurse'])
        sources = self._service.list_(self._backend, visible_tenants, **list_params)
        items = self.source_list_schema.dump(sources)
        filtered = self._service.count(self._backend, visible_tenants, **list_params)
        total = self._service.count(self._backend, visible_tenants)

        return {'total': total, 'filtered': filtered, 'items': items}

    def _prepare_new_source(self, source_data: SourceBody) -> SourceBody:
        return source_data

    def _create_new_source(
        self, source_data: SourceBody, tenant_uuid: str
    ) -> SourceInfo:
        body = self._service.create(
            self._backend, tenant_uuid=tenant_uuid, **source_data
        )
        return body

    def post(self) -> dict[str, Any]:
        tenant = Tenant.autodetect()
        args = self.source_schema.load(request.get_json(force=True))
        source_data = self._prepare_new_source(args)
        try:
            body = self._create_new_source(source_data, tenant.uuid)
        except InvalidSourceConfigError as ex:
            raise InvalidSourceConfigAPIError(ex.source_info)
        else:
            result: dict[str, Any] = self.source_schema.dump(body)
            return result


class SourceItem(_BaseSourceResource):
    def delete(self, source_uuid: str) -> tuple[str, int]:
        visible_tenants = get_tenant_uuids(recurse=True)
        self._service.delete(self._backend, source_uuid, visible_tenants)
        return '', 204

    def get(self, source_uuid: str) -> dict[str, Any]:
        visible_tenants = get_tenant_uuids(recurse=True)
        body = self._service.get(self._backend, source_uuid, visible_tenants)
        result: dict[str, Any] = self.source_schema.dump(body)
        return result

    def _prepare_source_update(self, source_data: SourceBody) -> SourceBody:
        return source_data

    def _edit_source(
        self, source_uuid: str, visible_tenants: list[str], source_data: SourceBody
    ) -> SourceInfo:
        body = self._service.edit(
            self._backend, source_uuid, visible_tenants, source_data
        )
        return body

    def put(self, source_uuid: str) -> tuple[str, int]:
        visible_tenants = get_tenant_uuids(recurse=True)
        args = self.source_schema.load(request.get_json(force=True))
        source_data = self._prepare_source_update(args)
        try:
            self._edit_source(source_uuid, visible_tenants, source_data)
        except InvalidSourceConfigError as ex:
            raise InvalidSourceConfigAPIError(ex.source_info)
        else:
            return '', 204


class BackendViewConfig(TypedDict):
    auth: AuthConfig


class BackendViewServices(TypedDict):
    source: _SourceService


class BackendViewDependencies(TypedDict):
    api: Api
    config: BackendViewConfig
    services: BackendViewServices


class BaseBackendView(BaseViewPlugin):
    _required_members = ['backend', 'list_resource', 'item_resource']
    backend: str
    list_resource: type[SourceList]
    item_resource: type[SourceItem]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        members = [getattr(self, name, None) for name in self._required_members]
        if None in members:
            msg = (
                f'{self.__class__.__name__} should have '
                f'the following members: {self._required_members}'
            )
            raise Exception(msg)

        super().__init__(*args, **kwargs)

    def _get_view_args(
        self, dependencies: BackendViewDependencies
    ) -> tuple[str, _SourceService, AuthConfig]:
        config = dependencies['config']
        service = dependencies['services']['source']

        return (self.backend, service, config['auth'])

    def load(self, dependencies: BackendViewDependencies) -> None:  # type: ignore[override]
        api = dependencies['api']

        args = self._get_view_args(dependencies)

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
