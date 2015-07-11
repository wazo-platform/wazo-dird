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

    def __init__(self, enabled_backends, source_configs):
        self._enabled_backends = enabled_backends
        self._source_configs = source_configs
        self._configs_by_backend = defaultdict(list)
        self._sources = {}

    def should_load_backend(self, extension):
        return extension.name in self._enabled_backends

    def load_sources(self):
        manager = enabled.EnabledExtensionManager(
            namespace=self._namespace,
            check_func=self.should_load_backend,
            invoke_on_load=False,
        )
        self._load_all_configs()
        manager.map(self._load_sources_using_backend, self._configs_by_backend)
        return self._sources

    def _load_all_configs(self):
        for source_config in self._source_configs.itervalues():
            source_type = source_config.get('type')
            if source_type:
                self._configs_by_backend[source_type].append(source_config)

    def _load_sources_using_backend(self, extension, configs_by_backend):
        backend = extension.name
        for config in configs_by_backend[backend]:
            try:
                config_name = config['name']
            except KeyError:
                logger.warning('One of the config for back-end `%s` has no name. Ignoring.', backend)
                logger.debug('Source config with no name: `%s`', config)
                continue
            try:
                source = extension.plugin()
                source.name = config_name
                source.load({'config': config})
                self._sources[source.name] = source
            except Exception:
                logger.exception('Failed to load back-end `%s` with config `%s`', extension.name, config_name)
