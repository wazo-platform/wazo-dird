# Copyright 2014-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from collections.abc import Mapping
from functools import partial
from typing import TYPE_CHECKING, Any, TypedDict

from stevedore import NamedExtensionManager
from stevedore.extension import Extension
from xivo import plugin_helpers

if TYPE_CHECKING:
    from flask import Flask
    from flask_restful import Api
    from wazo_auth_client import Client as AuthClient
    from wazo_confd_client import Client as ConfdClient
    from xivo.status import StatusAggregator

    from wazo_dird.bus import CoreBus
    from wazo_dird.config import Config
    from wazo_dird.controller import Controller
    from wazo_dird.helpers import BaseService
    from wazo_dird.http_server import CoreRestApi
    from wazo_dird.source_manager import SourceManager


logger = logging.getLogger(__name__)
services_extension_manager: NamedExtensionManager | None = None
views_extension_manager: NamedExtensionManager | None = None


class ServiceDependencies(TypedDict):
    config: Config
    source_manager: SourceManager
    bus: CoreBus
    controller: Controller
    auth_client: AuthClient
    confd_client: ConfdClient


def load_services(
    config: Config,
    enabled_services: dict[str, bool],
    source_manager: SourceManager,
    bus: CoreBus,
    controller: Controller,
) -> dict[str, Any]:
    global services_extension_manager
    dependencies: ServiceDependencies = {
        'config': config,
        'source_manager': source_manager,
        'bus': bus,
        'controller': controller,
        'auth_client': controller.auth_client,
        'confd_client': controller.confd_client,
    }

    loaded = _load_plugins('wazo_dird.services', enabled_services, dependencies)
    assert loaded is not None
    services_extension_manager, services = loaded
    return services


def unload_services() -> None:
    if services_extension_manager:
        services_extension_manager.map_method('unload')


def unload_views() -> None:
    def unload_view(ext: Extension, *args: Any, **kwargs: Any) -> None:
        if hasattr(ext.obj, 'unload'):
            logger.info('unloading view: %s', ext.name)
            ext.obj.unload()

    if views_extension_manager:
        views_extension_manager.map(unload_view)


class ViewDependencies(TypedDict):
    config: Config
    services: dict[str, BaseService]
    auth_client: AuthClient
    api: Api
    flask_app: Flask
    status_aggregator: StatusAggregator


def load_views(
    config: Config,
    enabled_views: dict[str, bool],
    services: dict[str, BaseService],
    auth_client: AuthClient,
    status_aggregator: StatusAggregator,
    rest_api: CoreRestApi,
) -> dict[str, Any]:
    global views_extension_manager
    dependencies: ViewDependencies = {
        'config': config,
        'services': services,
        'auth_client': auth_client,
        'api': rest_api.api,
        'flask_app': rest_api.app,
        'status_aggregator': status_aggregator,
    }
    loaded = _load_plugins('wazo_dird.views', enabled_views, dependencies)
    assert loaded is not None
    views_extension_manager, views = loaded
    return views


def _load_plugins(
    namespace: str, names: dict[str, bool], dependencies: Mapping[str, Any]
) -> tuple[NamedExtensionManager, dict[str, Any]] | None:
    enabled = plugin_helpers.enabled_names(names)
    logger.debug('Enabled plugins: %s', enabled)
    if not enabled:
        logger.info('no enabled plugins')
        return None

    on_missing_entrypoints = partial(plugin_helpers.on_missing_entrypoints, namespace)
    manager = NamedExtensionManager(
        namespace,
        enabled,
        name_order=True,
        on_load_failure_callback=plugin_helpers.on_load_failure,
        on_missing_entrypoints_callback=on_missing_entrypoints,
        invoke_on_load=True,
    )

    def _load_plugin(
        ext: Extension, *args: Any, **kwargs: Any
    ) -> tuple[str, plugin_helpers.Plugin]:
        return ext.name, plugin_helpers.load_plugin(ext, *args, **kwargs)

    return manager, dict(manager.map(_load_plugin, dependencies))
