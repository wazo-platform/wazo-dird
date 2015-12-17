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
from consul import ConsulException
from contextlib import contextmanager
from requests import RequestException

from xivo_dird import BaseServicePlugin
from xivo_dird import helpers
from xivo_dird.core.consul import ls_from_consul

logger = logging.getLogger(__name__)

ContactID = namedtuple('ContactID', ['source', 'id'])

FAVORITES_SOURCE_KEY = 'xivo/private/{user_uuid}/contacts/favorites/{source}/'
FAVORITE_KEY = 'xivo/private/{user_uuid}/contacts/favorites/{source}/{contact_id}'


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


class _FavoritesService(object):

    class FavoritesServiceException(Exception):
        pass

    class NoSuchFavorite(ValueError):
        def __init__(self, contact_id):
            message = "No such favorite: {}".format(contact_id)
            super(_FavoritesService.NoSuchFavorite, self).__init__(message)

    def __init__(self, config, sources):
        self._config = config
        self._sources = sources
        self._favorites = []
        self._executor = ThreadPoolExecutor(max_workers=10)

    def stop(self):
        self._executor.shutdown()

    def _async_list(self, source, contact_ids, args):
        raise_stopper = helpers.RaiseStopper(return_on_raise=[])
        future = self._executor.submit(raise_stopper.execute, source.list, contact_ids, args)
        future.name = source.name
        return future

    def favorites(self, profile, token_infos):
        futures = []
        for source_name, ids in self.favorite_ids(profile, token_infos).iteritems():
            source = self._sources[source_name]
            futures.append(self._async_list(source, ids, {'token_infos': token_infos}))

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
            ids = self._favorite_ids_in_source(token_infos['auth_id'], source.name, token_infos['token'])
            result[source.name] = ids
        return result

    def _favorite_ids_in_source(self, uuid, source_name, token):
        source_key = FAVORITES_SOURCE_KEY.format(user_uuid=uuid, source=source_name)
        with self._consul() as consul:
            _, keys = consul.kv.get(source_key, keys=True, token=token)
        return ls_from_consul(source_key, keys)

    def new_favorite(self, source, contact_id, token_infos):
        contact_id = contact_id.encode('utf-8')
        key = FAVORITE_KEY.format(user_uuid=token_infos['auth_id'], source=source, contact_id=contact_id)
        with self._consul() as consul:
            consul.kv.put(key, value=contact_id, token=token_infos['token'])

    def remove_favorite(self, source, contact_id, token_infos):
        key = FAVORITE_KEY.format(user_uuid=token_infos['auth_id'], source=source, contact_id=contact_id)
        with self._consul() as consul:
            _, value = consul.kv.get(key, token=token_infos['token'])

        if value is None:
            raise self.NoSuchFavorite((source, contact_id))

        with self._consul() as consul:
            consul.kv.delete(key, token=token_infos['token'])

    def _source_by_profile(self, profile):
        favorites_config = self._config.get('services', {}).get('favorites', {})
        try:
            source_names = favorites_config[profile]['sources']
        except KeyError:
            logger.warning('Cannot find lookup sources for profile %s', profile)
            return []
        else:
            return [self._sources[name] for name in source_names if name in self._sources]

    @contextmanager
    def _consul(self):
        try:
            yield Consul(**self._config['consul'])
        except ConsulException as e:
            raise self.FavoritesServiceException('Error from Consul: {}'.format(str(e)))
        except RequestException as e:
            raise self.FavoritesServiceException('Error while connecting to Consul: {}'.format(str(e)))
