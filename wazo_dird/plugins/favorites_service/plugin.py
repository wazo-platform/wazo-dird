# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from collections import defaultdict, namedtuple

from concurrent.futures import ALL_COMPLETED
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait
from xivo_bus.resources.directory.event import FavoriteAddedEvent, FavoriteDeletedEvent
from wazo_dird import BaseServicePlugin, helpers
from wazo_dird import database, exception
from wazo_dird.database.helpers import Session

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
            controller = args['controller']
        except KeyError:
            msg = ('%s should be loaded with "config", "source_manager" and "bus" but received: %s'
                   % (self.__class__.__name__, ','.join(args.keys())))
            raise ValueError(msg)

        crud = database.FavoriteCRUD(Session)

        self._service = _FavoritesService(config, source_manager, controller, crud, bus)
        return self._service

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

    def __init__(self, config, source_manager, controller, crud, bus):
        super().__init__(config, source_manager, crud, bus)
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._crud = crud
        self._bus = bus
        self._xivo_uuid = config.get('uuid')
        self._source_manager = source_manager
        self._controller = controller
        if not self._xivo_uuid:
            logger.info('loaded without a UUID: published events will be incomplete')

    def _available_sources(self, tenant_uuid):
        source_service = self._controller.services['source']
        sources = source_service.list_(None, [tenant_uuid])
        return sources

    def stop(self):
        self._executor.shutdown()

    def _async_list(self, source, contact_ids, args):
        raise_stopper = helpers.RaiseStopper(return_on_raise=[])
        future = self._executor.submit(raise_stopper.execute, source.list, contact_ids, args)
        future.name = source.name
        return future

    def favorites(self, profile_config, xivo_user_uuid, token=None):
        favorites_config = profile_config.get('services', {}).get('favorites', {})
        if not favorites_config:
            raise self.NoSuchProfileException(profile_config['name'])

        args = {
            'token_infos': {'xivo_user_uuid': xivo_user_uuid},
            'token': token,
            'xivo_user_uuid': xivo_user_uuid,
        }
        futures = []
        favorite_map = self.favorite_ids(profile_config, xivo_user_uuid).by_uuid
        for source_uuid, ids in favorite_map.items():
            source = self._source_manager.get(source_uuid)
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

    def favorite_ids(self, profile_config, xivo_user_uuid):
        favorites = self._crud.get(xivo_user_uuid)
        favorite_config = profile_config.get('services', {}).get('favorites', {})
        enabled_sources = {source['name']: source for source in favorite_config.get('sources', [])}

        by_uuid = defaultdict(list)
        by_name = defaultdict(list)
        for name, id_ in favorites:
            source = enabled_sources.get(name)
            if not source:
                continue
            by_uuid[source['uuid']].append(id_)
            by_name[source['name']].append(id_)

        FavoriteList = namedtuple('FavoriteList', ['by_uuid', 'by_name'])
        return FavoriteList(by_uuid, by_name)

    def new_favorite(self, tenant_uuid, source_name, contact_id, xivo_user_uuid):
        sources = self._available_sources(tenant_uuid)
        matching_source = None
        for source in sources:
            if source['name'] == source_name:
                matching_source = source
                break

        if not matching_source:
            raise self.NoSuchSourceException(source_name)

        backend = source['backend']
        self._crud.create(xivo_user_uuid, backend, source_name, contact_id)
        event = FavoriteAddedEvent(self._xivo_uuid, xivo_user_uuid, source_name, contact_id)
        try:
            self._bus.publish(event, headers={'user_uuid:{uuid}'.format(uuid=xivo_user_uuid): True})
        except OSError as e:
            logger.error('failed to publish bus event %s', e)
            logger.info('%s', event)

    def remove_favorite(self, tenant_uuid, source_name, contact_id, xivo_user_uuid):
        sources = self._available_sources(tenant_uuid)
        matching_source = None
        for source in sources:
            if source['name'] == source_name:
                matching_source = source
                break

        if not matching_source:
            raise self.NoSuchSourceException(source_name)

        self._crud.delete(xivo_user_uuid, source_name, contact_id)
        event = FavoriteDeletedEvent(self._xivo_uuid, xivo_user_uuid, source, contact_id)
        self._bus.publish(event, headers={'user_uuid:{uuid}'.format(uuid=xivo_user_uuid): True})
