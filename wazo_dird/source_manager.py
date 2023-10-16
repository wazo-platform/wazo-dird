# Copyright 2014-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import logging
import threading
from functools import partial
from typing import Protocol

import stevedore
from stevedore import NamedExtensionManager
from stevedore.extension import Extension
from wazo_auth_client import Client as AuthClient
from xivo import plugin_helpers
from xivo.token_renewer import TokenRenewer

from wazo_dird import exception
from wazo_dird.config import Config as MainConfig
from wazo_dird.plugins.base_plugins import (
    BaseSourcePlugin,
    SourceConfig,
    SourcePluginDependencies,
)

logger = logging.getLogger(__name__)


class SourceServiceProtocol(Protocol):
    def get_by_uuid(self, uuid: str) -> SourceConfig:
        ...


class SourceManager:
    _namespace = 'wazo_dird.backends'

    def __init__(
        self,
        enabled_backends: dict[str, bool],
        config: MainConfig,
        auth_client: AuthClient,
        token_renewer: TokenRenewer,
    ):
        self._enabled_backends = enabled_backends
        self._main_config = config
        self._sources: dict[str, BaseSourcePlugin | None] = {}
        self._config = config
        self._auth_client = auth_client
        self._token_renewer = token_renewer
        self._source_service: SourceServiceProtocol | None = None
        self._source_lock = threading.Lock()

    def get(self, source_uuid):
        assert self._source_service
        with self._source_lock:
            source = self._sources.get(source_uuid)
            if not source:
                self._sources[source_uuid] = self._load_source(source_uuid)

            return self._sources[source_uuid]

    def invalidate(self, source_uuid: str):
        with self._source_lock:
            self._sources.pop(source_uuid, None)

    def _load_source(self, source_uuid: str) -> BaseSourcePlugin | None:
        assert self._source_service
        try:
            source_config = self._source_service.get_by_uuid(source_uuid)
        except exception.NoSuchSource:
            logger.info('no source found with uuid %s', source_uuid)
            return None

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
            else:
                return None
        except stevedore.exception.NoMatches:
            return None

    def unload_sources(self):
        logger.info('unloading all source plugins')
        for source in self._sources.values():
            if source is not None:
                source.unload()

    def set_source_service(self, service: SourceServiceProtocol):
        self._source_service = service

    def _add_source_with_config(
        self, extension: Extension, config: SourceConfig
    ) -> BaseSourcePlugin:
        name = config['name']
        logger.debug('Loading source %s', name)
        try:
            source: BaseSourcePlugin = extension.plugin()
            source.name = name
            source.backend = extension.name
            dependencies = SourcePluginDependencies(
                {
                    'auth_client': self._auth_client,
                    'config': config,
                    'main_config': self._main_config,
                    'token_renewer': self._token_renewer,
                }
            )
            source.load(dependencies)
            self._sources[source.name] = source
        except Exception:
            logger.exception(
                'Failed to load back-end `%s` with config `%s`', extension.name, name
            )
        return source
