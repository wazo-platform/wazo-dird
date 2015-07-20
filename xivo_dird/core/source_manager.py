# -*- coding: utf-8 -*-

# Copyright (C) 2014-2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import logging

from collections import defaultdict
from stevedore import enabled


logger = logging.getLogger(__name__)


class SourceManager(object):

    _namespace = 'xivo_dird.backends'

    def __init__(self, enabled_backends, config):
        self._enabled_backends = enabled_backends
        self._source_configs = config['sources']
        self._main_config = config
        self._sources = {}

    def should_load_backend(self, extension):
        return extension.name in self._enabled_backends

    def load_sources(self):
        manager = enabled.EnabledExtensionManager(
            namespace=self._namespace,
            check_func=self.should_load_backend,
            invoke_on_load=False,
        )
        configs_by_backend = self.group_configs_by_backend(self._source_configs)
        manager.map(self._load_sources_using_backend, configs_by_backend)
        return self._sources

    def _load_sources_using_backend(self, extension, configs_by_backend):
        backend = extension.name
        for config in configs_by_backend[backend]:
            config_name = config['name']
            logger.debug('Loading source %s', config_name)
            try:
                source = extension.plugin()
                source.name = config_name
                source.load({'config': config,
                             'main_config': self._main_config})
                self._sources[source.name] = source
            except Exception:
                logger.exception('Failed to load back-end `%s` with config `%s`', extension.name, config_name)

    @staticmethod
    def group_configs_by_backend(source_configs):
        configs_by_backend = defaultdict(list)
        for source_config in source_configs.itervalues():
            source_type = source_config.get('type')
            if not source_type:
                logger.warning('One of the source config has no back-end type. Ignoring.')
                logger.debug('Source config with no type: `%s`', source_config)
                continue
            configs_by_backend[source_type].append(source_config)
        return configs_by_backend
