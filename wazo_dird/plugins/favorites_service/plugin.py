# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from concurrent.futures import ALL_COMPLETED
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait
from xivo_bus.resources.directory.event import FavoriteAddedEvent, FavoriteDeletedEvent
from wazo_dird import BaseServicePlugin, helpers
from wazo_dird import database, exception

logger = logging.getLogger(__name__)


class _NoSuchProfileException(ValueError):

    msg_tpl = 'No such profile in favorite service configuration: {}'

    def __init__(self, profile):
        msg = self.msg_tpl.format(profile)
        super().__init__(msg)


class _NoSuchSourceException(ValueError):

    msg_tpl = 'No such source: {}'

    def __init__(self, source):
        msg = self.msg_tpl.format(source)
        super().__init__(msg)


class FavoritesServicePlugin(BaseServicePlugin):

    def __init__(self):
        self._service = None

    def load(self, args):
        try:
            config = args['config']
            source_manager = args['source_manager']
            bus = args['bus']
        except KeyError:
            msg = ('%s should be loaded with "config", "source_manager" and "bus" but received: %s'
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

        self._service = _FavoritesService(config, source_manager, crud, bus)
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


class _FavoritesService(helpers.BaseService):

    NoSuchFavoriteException = exception.NoSuchFavorite
    NoSuchProfileException = _NoSuchProfileException
    NoSuchSourceException = _NoSuchSourceException
    DuplicatedFavoriteException = exception.DuplicatedFavoriteException
    _service_name = 'favorites'

    def __init__(self, config, source_manager, crud, bus):
        super().__init__(config, source_manager, crud, bus)
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._crud = crud
        self._bus = bus
        self._xivo_uuid = config.get('uuid')
        self._source_manager = source_manager
        if not self._xivo_uuid:
            logger.info('loaded without a UUID: published events will be incomplete')

    def _configured_profiles(self):
        return self._config.get('services', {}).get('favorites', {}).keys()

    def _available_sources(self):
        available_sources = set()
        for source_config in self._config.get('services', {}).get('favorites', {}).values():
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
        if profile not in self._configured_profiles():
            raise self.NoSuchProfileException(profile)

        args = {'token_infos': {'xivo_user_uuid': xivo_user_uuid}}
        futures = []
        for source_name, ids in self.favorite_ids(profile, xivo_user_uuid).items():
            source = self._source_manager.get(source_name)
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
        if profile not in self._configured_profiles():
            return []

        favorites = self._crud.get(xivo_user_uuid)
        enabled_sources = [source.name for source in self.source_by_profile(profile)]

        result = defaultdict(list)
        for name, id_ in favorites:
            if name not in enabled_sources:
                continue
            result[name].append(id_)

        return result

    def new_favorite(self, source, contact_id, xivo_user_uuid):
        if source not in self._available_sources():
            raise self.NoSuchSourceException(source)

        backend = self._source_backends[source]
        self._crud.create(xivo_user_uuid, backend, source, contact_id)
        event = FavoriteAddedEvent(self._xivo_uuid, xivo_user_uuid, source, contact_id)
        self._bus.publish(event, headers={'user_uuid:{uuid}'.format(uuid=xivo_user_uuid): True})

    def remove_favorite(self, source, contact_id, xivo_user_uuid):
        if source not in self._available_sources():
            raise self.NoSuchSourceException(source)

        self._crud.delete(xivo_user_uuid, source, contact_id)
        event = FavoriteDeletedEvent(self._xivo_uuid, xivo_user_uuid, source, contact_id)
        self._bus.publish(event, headers={'user_uuid:{uuid}'.format(uuid=xivo_user_uuid): True})
