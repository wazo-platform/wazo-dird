# Copyright 2014-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from stevedore import NamedExtensionManager
from xivo import plugin_helpers

from wazo_dird import rest_api

logger = logging.getLogger(__name__)
services_extension_manager = None


def load_services(config, enabled_services, source_manager, bus, controller):
    global services_extension_manager
    dependencies = {
        'config': config,
        'source_manager': source_manager,
        'bus': bus,
        'controller': controller,
    }

    services_extension_manager, services = _load_plugins(
        'wazo_dird.services',
        enabled_services,
        dependencies,
    )
    return services


def unload_services():
    if services_extension_manager:
        services_extension_manager.map_method('unload')


def load_views(config, enabled_views, services, auth_client):
    dependencies = {
        'config': config,
        'services': services,
        'auth_client': auth_client,
        'api': rest_api.api,
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
