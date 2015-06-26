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

from collections import namedtuple
from concurrent.futures import ALL_COMPLETED
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait
from consul import Consul

from xivo_dird import BaseService
from xivo_dird import BaseServicePlugin

logger = logging.getLogger(__name__)

ContactID = namedtuple('ContactID', ['source', 'id'])

FAVORITES_SOURCE_KEY = 'xivo/private/{user_uuid}/contacts/favorites/{source}'
FAVORITE_KEY = 'xivo/private/{user_uuid}/contacts/favorites/{source}/{contact_id}'


class NoSuchFavorite(ValueError):
    def __init__(self, contact_id):
        message = "No such favorite: {}".format(contact_id)
        super(NoSuchFavorite, self).__init__(message)


class FavoritesServicePlugin(BaseServicePlugin):

    def __init__(self):
        self._service = None

    def load(self, args):
        try:
            config = args['config']
            sources = args['sources']
        except KeyError:
            msg = ('%s should be loaded with "config" and "sources" but received: %s'
                   % (self.__class__.__name__, ','.join(args.keys())))
            raise ValueError(msg)

        self._service = _FavoritesService(config, sources)
        return self._service

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

    def __call__(self, profile, token_infos):
        return self.favorites(profile, token_infos)

    def favorites(self, profile, token_infos):
        futures = []
        for source_name, ids in self.favorite_ids(profile, token_infos).iteritems():
            source = self._sources[source_name]
            futures.append(self._async_list(source, ids))

        params = {'return_when': ALL_COMPLETED}
        if 'lookup_timeout' in self._config:
            params['timeout'] = self._config['lookup_timeout']

        done, _ = wait(futures, **params)
        results = []
        for future in done:
            for result in future.result():
                results.append(result)
        return results

    def favorite_ids(self, profile, token_infos):
        result = {}
        for source in self._source_by_profile(profile):
            ids = self._favorite_ids_in_source(token_infos['uuid'], source.name, token_infos['token'])
            result[source.name] = ids
        return result

    def _favorite_ids_in_source(self, uuid, source_name, token):
        source_key = FAVORITES_SOURCE_KEY.format(user_uuid=uuid, source=source_name)
        _, keys = self._consul().kv.get(source_key, keys=True, token=token)
        ids = []
        if keys:
            for key in keys:
                logger.error(key)
                _, result = self._consul().kv.get(key, token=token)
                logger.error(result)
                ids.append(result['Value'])
        return ids

    def new_favorite(self, source, contact_id, token_infos):
        key = FAVORITE_KEY.format(user_uuid=token_infos['uuid'], source=source, contact_id=contact_id)
        self._consul().kv.put(key, value=contact_id, token=token_infos['token'])

    def remove_favorite(self, source, contact_id, token_infos):
        key = FAVORITE_KEY.format(user_uuid=token_infos['uuid'], source=source, contact_id=contact_id)
        self._consul().kv.delete(key, token=token_infos['token'])

    def _source_by_profile(self, profile):
        favorites_config = self._config.get('services', {}).get('favorites', {})
        try:
            source_names = favorites_config[profile]['sources']
        except KeyError:
            logger.warning('Cannot find lookup sources for profile %s', profile)
            return []
        else:
            return [self._sources[name] for name in source_names if name in self._sources]

    def _consul(self):
        return Consul(**self._config['consul'])
