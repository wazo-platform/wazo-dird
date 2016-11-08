# -*- coding: utf-8 -*-

# Copyright (C) 2015-2016 Avencall
# Copyright (C) 2016 Proformatique, Inc.
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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from concurrent.futures import ALL_COMPLETED
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait

from xivo_dird import BaseServicePlugin, helpers
from xivo_dird.core import database, exception

logger = logging.getLogger(__name__)


class _NoSuchProfileException(ValueError):

    msg_tpl = 'No such profile in favorite service configuration: {}'

    def __init__(self, profile):
        msg = self.msg_tpl.format(profile)
        super(_NoSuchProfileException, self).__init__(msg)


class _NoSuchSourceException(ValueError):

    msg_tpl = 'No such source: {}'

    def __init__(self, source):
        msg = self.msg_tpl.format(source)
        super(_NoSuchSourceException, self).__init__(msg)


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

        try:
            db_uri = config['db_uri']
        except KeyError:
            msg = '{} should be loaded with a config containing "db_uri" but received: {}'.format(
                self.__class__.__name__, ','.join(config.keys())
            )
            raise ValueError(msg)

        crud = self._new_favorite_crud(db_uri)

        self._service = _FavoritesService(config, sources, crud)
        return self._service

    def _new_favorite_crud(self, db_uri):
        self._Session = scoped_session(sessionmaker())
        engine = create_engine(db_uri)
        self._Session.configure(bind=engine)
        return database.FavoriteCRUD(self._Session)

    def unload(self):
        if self._service:
            self._service.stop()
            self._service = None


class _FavoritesService(object):

    NoSuchFavoriteException = exception.NoSuchFavorite
    NoSuchProfileException = _NoSuchProfileException
    NoSuchSourceException = _NoSuchSourceException
    DuplicatedFavoriteException = exception.DuplicatedFavoriteException

    def __init__(self, config, sources, crud):
        self._config = config
        self._sources = sources
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._crud = crud

    @property
    def _configured_profiles(self):
        return self._config.get('services', {}).get('favorites', {}).keys()

    @property
    def _available_sources(self):
        available_sources = set()
        for source_config in self._config.get('services', {}).get('favorites', {}).itervalues():
            for source in source_config.get('sources', []):
                available_sources.add(source)
        return list(available_sources)

    def stop(self):
        self._executor.shutdown()

    def _async_list(self, source, contact_ids, args):
        raise_stopper = helpers.RaiseStopper(return_on_raise=[])
        future = self._executor.submit(raise_stopper.execute, source.list, contact_ids, args)
        future.name = source.name
        return future

    def favorites(self, profile, xivo_user_uuid):
        if profile not in self._configured_profiles:
            raise self.NoSuchProfileException(profile)

        args = {'token_infos': {'xivo_user_uuid': xivo_user_uuid}}
        futures = []
        for source_name, ids in self.favorite_ids(profile, xivo_user_uuid).iteritems():
            source = self._sources[source_name]
            futures.append(self._async_list(source, ids, args))

        params = {'return_when': ALL_COMPLETED}
        if 'lookup_timeout' in self._config:
            params['timeout'] = self._config['lookup_timeout']

        done, _ = wait(futures, **params)
        results = []
        for future in done:
            for result in future.result():
                results.append(result)
        return results

    def favorite_ids(self, profile, xivo_user_uuid):
        if profile not in self._configured_profiles:
            raise self.NoSuchProfileException(profile)

        favorites = self._crud.get(xivo_user_uuid)
        enabled_sources = [source.name for source in self._source_by_profile(profile)]

        result = defaultdict(list)
        for name, id_ in favorites:
            if name not in enabled_sources:
                continue
            result[name].append(id_)

        return result

    def new_favorite(self, source, contact_id, xivo_user_uuid):
        if source not in self._available_sources:
            raise self.NoSuchSourceException(source)

        contact_id = contact_id.encode('utf-8')
        self._crud.create(xivo_user_uuid, source, contact_id)

    def remove_favorite(self, source, contact_id, xivo_user_uuid):
        if source not in self._available_sources:
            raise self.NoSuchSourceException(source)

        self._crud.delete(xivo_user_uuid, source, contact_id)

    def _source_by_profile(self, profile):
        favorites_config = self._config.get('services', {}).get('favorites', {})
        try:
            source_names = favorites_config[profile]['sources']
        except KeyError:
            logger.warning('Cannot find lookup sources for profile %s', profile)
            return []
        else:
            return [self._sources[name] for name in source_names if name in self._sources]
