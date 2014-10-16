# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import logging
import os
import yaml

from collections import defaultdict
from stevedore import enabled
from xivo_dird import BaseServicePlugin

logger = logging.getLogger(__name__)


class LookupServicePlugin(BaseServicePlugin):

    def load(self, args=None):
        if not args:
            args = {}

        if 'config' not in args:
            raise ValueError('Missing config in %s' % args)

        self._service = _LookupService(args['config'])

    def unload(self, args=None):
        pass


class _LookupService(object):

    def __init__(self, config):
        self._config = config
        self._source_manager = _SourceManager(config)

    def lookup(self, term, profile, user_id):
        args = {'user_id': user_id}

        for source, columns in self._source_manager.get_by_profile(profile):
            for result in source.search(term, args, columns):
                yield result


class _SourceManager(object):

    _namespace = 'xivo-dird.backends'

    def __init__(self, config):
        self._config = config
        self._configs_by_backend = defaultdict(list)
        self._sources = []

    def should_load_backend(self, extension):
        return extension.name in self._config.get('source_plugins', [])

    def load_backends(self):
        manager = enabled.EnabledExtensionManager(
            namespace=self._namespace,
            check_func=self.should_load_backend,
            invoke_on_load=False,
        )
        self._load_all_configs()
        manager.man(self._load_source)

    def get_by_profile(self):
        '''
        generates a list of source, column pairs
        '''

    def _load_all_configs(self):
        if 'plugin_config_dir' not in self._config:
            logger.warning('No configured "plugin_config_dir"')
            return

        source_config_files = []
        for dir_path, _, file_names in os.walk(self._config['plugin_config_dir']):
            for file_name in file_names:
                full_filename = os.path.join(dir_path, file_name)
                source_config_files.append(full_filename)

        for config_file in source_config_files:
            try:
                with open(config_file) as f:
                    config = yaml.load(f)
                    self._configs_by_backens[config['type']].append(config)
            except Exception:
                logger.warning('Failed to load %s', config_file)

    def _load_source(self, extension):
        backend = extension.name
        for config in self._configs_by_backens[backend]:
            source = extension.plugin()
            source.load(config)
            self._sources.append(source)
