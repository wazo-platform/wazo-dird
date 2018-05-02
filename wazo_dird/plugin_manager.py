# -*- coding: utf-8 -*-
# Copyright 2014-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from stevedore import NamedExtensionManager
from xivo import plugin_helpers

from .source_manager import SourceManager

logger = logging.getLogger(__name__)
services_extension_manager = None
source_manager = None


def load_services(config, enabled_services, sources, bus):
    global services_extension_manager
    dependencies = {
        'config': config,
        'sources': sources,
        'bus': bus,
    }
    services_extension_manager, services = _load_plugins('wazo_dird.services', enabled_services, dependencies)
    return services


def unload_services():
    if services_extension_manager:
        services_extension_manager.map_method('unload')


def load_sources(enabled_backends, source_configs):
    global source_manager
    if not source_manager:
        source_manager = SourceManager(enabled_backends, source_configs)
    return source_manager.load_sources()


def unload_sources():
    if not source_manager:
        return

    return source_manager.unload_sources()


def load_views(config, enabled_views, services, rest_api):
    dependencies = {
        'config': config,
        'http_app': rest_api.app,
        'rest_api': rest_api.api,
        'services': services,
    }
    views_extension_manager, views = _load_plugins('wazo_dird.views', enabled_views, dependencies)
    return views


def _load_plugins(namespace, names, dependencies):
    names = plugin_helpers.enabled_names(names)
    logger.debug('Enabled plugins: %s', names)
    if not names:
        logger.info('no enabled plugins')
        return

    manager = NamedExtensionManager(
        namespace,
        names,
        name_order=True,
        on_load_failure_callback=plugin_helpers.on_load_failure,
        on_missing_entrypoints_callback=plugin_helpers.on_missing_entrypoints,
        invoke_on_load=True
    )

    def _load_plugin(ext, *args, **kwargs):
        return ext.name, plugin_helpers.load_plugin(ext, *args, **kwargs)

    return manager, dict(manager.map(_load_plugin, dependencies))
