# -*- coding: utf-8 -*-

# Copyright (C) 2015 Avencall
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

from concurrent.futures import ALL_COMPLETED
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait
from collections import namedtuple

from xivo_dird import BaseService
from xivo_dird import BaseServicePlugin

logger = logging.getLogger(__name__)


class FavoritesServicePlugin(BaseServicePlugin):

    def __init__(self):
        self._service = None

    def load(self, args):
        try:
            self._service = _FavoritesService(args['config'], args['sources'])
            return self._service
        except KeyError:
            msg = ('%s should be loaded with "config" and "sources" but received: %s'
                   % (self.__class__.__name__, ','.join(args.keys())))
            raise ValueError(msg)

    def unload(self):
        if self._service:
            self._service.stop()
            self._service = None


class _FavoritesService(BaseService):

    def __init__(self, config, sources):
        self._config = config
        self._sources = sources
        self._favorites = []
        self._executor = ThreadPoolExecutor(max_workers=10)

    def stop(self):
        self._executor.shutdown()

    def _async_list(self, source, contact_ids):
        future = self._executor.submit(source.list, contact_ids)
        future.name = source.name
        return future

    def __call__(self, profile):
        return self.favorites(profile)

    def favorites(self, profile):
        futures = []
        for source in self._source_by_profile(profile):
            contact_ids = [contact_id.id for contact_id in self._favorites if contact_id.source == source.name]
            futures.append(self._async_list(source, contact_ids))

        params = {'return_when': ALL_COMPLETED}
        if 'lookup_timeout' in self._config:
            params['timeout'] = self._config['lookup_timeout']

        done, _ = wait(futures, **params)
        results = []
        for future in done:
            for result in future.result():
                results.append(result)
        return results

    def new_favorite(self, source, contact_id):
        self._favorites.append(ContactID(source, contact_id))

    def remove_favorite(self, source, contact_id):
        self._favorites.remove(ContactID(source, contact_id))

    def _source_by_profile(self, profile):
        try:
            source_names = self._config[profile]['sources']
        except KeyError:
            logger.warning('Cannot find lookup sources for profile %s', profile)
            return []
        else:
            return [self._sources[name] for name in source_names if name in self._sources]


ContactID = namedtuple('ContactID', ['source', 'id'])
