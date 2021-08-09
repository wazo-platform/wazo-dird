# Copyright 2014-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import threading


import stevedore
from functools import partial
from stevedore import NamedExtensionManager

from xivo import plugin_helpers

from wazo_dird import exception

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

    def get(self, source_uuid):
        with self._source_lock:
            source = self._sources.get(source_uuid)
            if not source:
                self._sources[source_uuid] = self._load_source(source_uuid)

            return self._sources[source_uuid]

    def invalidate(self, source_uuid):
        with self._source_lock:
            self._sources.pop(source_uuid, None)

    def _load_source(self, source_uuid):
        try:
            source_config = self._source_service.get_by_uuid(source_uuid)
        except exception.NoSuchSource:
            logger.info('no source found with uuid %s', source_uuid)
            return

        on_missing_entrypoints = partial(
            plugin_helpers.on_missing_entrypoints,
            self._namespace,
        )
        manager = NamedExtensionManager(
            self._namespace,
            [source_config['backend']],
            on_load_failure_callback=plugin_helpers.on_load_failure,
            on_missing_entrypoints_callback=on_missing_entrypoints,
            invoke_on_load=True,
        )

        def load(extension):
            return self._add_source_with_config(extension, source_config)

        try:
            for result in manager.map(load):
                return result
        except stevedore.exception.NoMatches:
            return None

    def unload_sources(self):
        logger.info('unloading all source plugins')
        for source in self._sources.values():
            if source is not None:
                source.unload()

    def set_source_service(self, service):
        self._source_service = service

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
            logger.exception(
                'Failed to load back-end `%s` with config `%s`', extension.name, name
            )
        return source
