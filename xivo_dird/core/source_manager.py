# -*- coding: utf-8 -*-

# Copyright (C) 2014 Avencall
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
import os

from collections import defaultdict
from stevedore import enabled


logger = logging.getLogger(__name__)


class SourceManager(object):

    _namespace = 'xivo-dird.backends'

    def __init__(self, config):
        self._config = config
        self._configs_by_backend = defaultdict(list)
        self._sources = []

    def should_load_backend(self, extension):
        return extension.name in self._config.get('source_plugins', [])

    def load_sources(self):
        manager = enabled.EnabledExtensionManager(
            namespace=self._namespace,
            check_func=self.should_load_backend,
            invoke_on_load=False,
        )
        self._load_all_configs()
        manager.map(self._load_sources_using_backend, self._configs_by_backend)

    def _load_all_configs(self):
        if 'plugin_config_dir' not in self._config:
            logger.warning('No configured "plugin_config_dir"')
            return

        source_config_files = _list_files(self._config['plugin_config_dir'])

        for config_file in source_config_files:
            config = _load_yaml_content(config_file)
            if not config or 'type' not in config:
                continue

            self._configs_by_backend[config['type']].append(config)

    def _load_sources_using_backend(self, extension, configs_by_backend):
        backend = extension.name
        for config in configs_by_backend[backend]:
            source = extension.plugin()
            source.name = config.get('name')
            source.load(config)
            self._sources.append(source)


def _list_files(directory):
    result = []

    for dir_path, _, file_names in os.walk(directory):
        for file_name in file_names:
            full_filename = os.path.join(dir_path, file_name)
            result.append(full_filename)

    return result


def _load_yaml_content(full_filename):
    with open(full_filename) as f:
        try:
            return yaml.load(f)
        except AttributeError:
            logger.warning('Failed to load yaml config from %s', full_filename)

    return {}
