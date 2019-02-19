# Copyright 2014-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import threading

from collections import defaultdict

import stevedore
from stevedore import (
    EnabledExtensionManager,
    NamedExtensionManager,
)
from xivo import plugin_helpers


logger = logging.getLogger(__name__)


class SourceManager:

    _namespace = 'wazo_dird.backends'

    def __init__(self, enabled_backends, config, auth_client, token_renewer):
        self._enabled_backends = enabled_backends
        self._main_config = config
        self._sources = {}
        self._config = config
        self._auth_client = auth_client
        self._token_renewer = token_renewer
        self._source_service = None
        self._source_lock = threading.Lock()

    def get(self, source_name):
        # XXX the parameter will be a UUID at the end of the migration making the source unique
        with self._source_lock:
            source = self._sources.get(source_name)
            if not source:
                self._sources[source_name] = self._load_source(source_name)

            return self._sources[source_name]

    def _load_source(self, source_name):
        source_config = self._source_service.get_by_name(source_name)
        if not source_config:
            logger.info('no config found for %s', source_name)
            return

        manager = NamedExtensionManager(
            self._namespace,
            [source_config['backend']],
            on_load_failure_callback=plugin_helpers.on_load_failure,
            on_missing_entrypoints_callback=plugin_helpers.on_missing_entrypoints,
            invoke_on_load=True,
        )

        def load(extension):
            return self._add_source_with_config(extension, source_config)

        try:
            for result in manager.map(load):
                return result
        except stevedore.exception.NoMatches:
            return None

    # XXX remove?
    def load_sources(self):
        names = plugin_helpers.enabled_names(self._enabled_backends)
        logger.debug('Enabled plugins: %s', names)
        manager = NamedExtensionManager(
            self._namespace,
            names,
            name_order=True,
            on_load_failure_callback=plugin_helpers.on_load_failure,
            on_missing_entrypoints_callback=plugin_helpers.on_missing_entrypoints,
            invoke_on_load=True
        )

        configs_by_backend = self.group_configs_by_backend(self._source_configs)
        manager.map(self._load_sources_using_backend, configs_by_backend)
        return self._sources

    def unload_sources(self):
        logger.info('unloading all source plugins')
        for source in self._sources.values():
            if source is not None:
                source.unload()

    def set_source_service(self, service):
        self._source_service = service

    # XXX remove?
    def _is_enabled(self, extension):
        return extension.name in self._enabled_backends

    # XXX remove?
    def load_source(self, type_, name):
        manager = EnabledExtensionManager(
            namespace=self._namespace,
            check_func=lambda extension: extension.name == type_,
            invoke_on_load=False,
        )
        manager.map(self._add_source, name)

    # XXX remove?
    def _add_source(self, extension, name):
        config = self._source_configs.get(name)
        if not config:
            logger.info('no config found for %s', name)
            return

        self._add_source_with_config(extension, config)

    def _add_source_with_config(self, extension, config):
        name = config['name']
        logger.debug('Loading source %s', name)
        try:
            source = extension.plugin()
            source.name = name
            source.backend = extension.name
            dependencies = {
                'auth_client': self._auth_client,
                'config': config,
                'main_config': self._main_config,
                'token_renewer': self._token_renewer,
            }
            source.load(dependencies)
            self._sources[source.name] = source
        except Exception:
            logger.exception('Failed to load back-end `%s` with config `%s`',
                             extension.name, name)
        return source

    # XXX remove?
    def _load_sources_using_backend(self, extension, configs_by_backend):
        for config in configs_by_backend.get(extension.name, []):
            self._add_source_with_config(extension, config)

    # XXX remove?
    @staticmethod
    def group_configs_by_backend(source_configs):
        configs_by_backend = defaultdict(list)
        for source_config in source_configs.values():
            source_type = source_config.get('type')
            if not source_type:
                logger.warning('One of the source config has no back-end type. Ignoring.')
                logger.debug('Source config with no type: `%s`', source_config)
                continue
            configs_by_backend[source_type].append(source_config)
        return configs_by_backend
