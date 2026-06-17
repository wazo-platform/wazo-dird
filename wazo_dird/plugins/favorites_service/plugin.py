# Copyright 2015-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from collections import defaultdict, namedtuple
from concurrent.futures import ALL_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import TYPE_CHECKING, Any, cast

from wazo_bus.resources.directory.event import FavoriteAddedEvent, FavoriteDeletedEvent

from wazo_dird import BaseServicePlugin, BaseSourcePlugin, database, exception, helpers
from wazo_dird.database.helpers import Session
from wazo_dird.helpers import ProfileConfig
from wazo_dird.plugins.base_plugins import SourceConfig
from wazo_dird.plugins.source_result import _SourceResult

if TYPE_CHECKING:
    from wazo_dird.bus import CoreBus
    from wazo_dird.controller import Controller
    from wazo_dird.database.queries.source import SourceInfo
    from wazo_dird.plugin_manager import ServiceDependencies
    from wazo_dird.source_manager import SourceManager

logger = logging.getLogger(__name__)


class _NoSuchProfileException(ValueError):
    msg_tpl = 'No such profile in favorite service configuration: {}'

    def __init__(self, profile: str) -> None:
        msg = self.msg_tpl.format(profile)
        super().__init__(msg)


class _NoSuchSourceException(ValueError):
    msg_tpl = 'No such source: {}'

    def __init__(self, source: str) -> None:
        msg = self.msg_tpl.format(source)
        super().__init__(msg)


class FavoritesServicePlugin(BaseServicePlugin):
    def __init__(self) -> None:
        self._service: _FavoritesService | None = None

    def load(self, args: ServiceDependencies) -> _FavoritesService:
        try:
            config = cast('dict[str, Any]', args['config'])
            source_manager = args['source_manager']
            bus = args['bus']
            controller = args['controller']
        except KeyError:
            msg = (
                '%s should be loaded with "config", "source_manager" and "bus" but received: %s'
                % (self.__class__.__name__, ','.join(args.keys()))
            )
            raise ValueError(msg)

        crud = database.FavoriteCRUD(Session)

        self._service = _FavoritesService(config, source_manager, controller, crud, bus)
        return self._service

    def unload(self) -> None:
        if self._service:
            self._service.stop()
            self._service = None


class _FavoritesService(helpers.BaseService):
    NoSuchFavoriteException = exception.NoSuchFavorite
    NoSuchProfileException = _NoSuchProfileException
    NoSuchSourceException = _NoSuchSourceException
    DuplicatedFavoriteException = exception.DuplicatedFavoriteException
    _service_name = 'favorites'

    def __init__(
        self,
        config: dict[str, Any],
        source_manager: SourceManager,
        controller: Controller,
        crud: database.FavoriteCRUD,
        bus: CoreBus,
    ) -> None:
        super().__init__(config, source_manager, controller, crud, bus)
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._crud = crud
        self._bus = bus
        self._xivo_uuid = config.get('uuid')
        self._source_manager = source_manager
        self._controller = controller
        if not self._xivo_uuid:
            logger.info('loaded without a UUID: published events will be incomplete')

    def _available_sources(self, tenant_uuid: str) -> list[SourceInfo]:
        source_service = self._controller.services['source']
        sources: list[SourceInfo] = source_service.list_(None, [tenant_uuid])
        return sources

    def stop(self) -> None:
        self._executor.shutdown()

    def _async_list(
        self,
        source: BaseSourcePlugin,
        contact_ids: list[str],
        args: dict[str, Any],
    ) -> Future[list[_SourceResult]]:
        raise_stopper: helpers.RaiseStopper[list[_SourceResult]] = helpers.RaiseStopper(
            return_on_raise=[]
        )
        future = self._executor.submit(
            raise_stopper.execute, source.list, contact_ids, args
        )
        setattr(future, 'name', source.name)
        return future

    def favorites(
        self,
        profile_config: ProfileConfig,
        user_uuid: str,
        token: str | None = None,
    ) -> list[_SourceResult]:
        favorites_config = profile_config.get('services', {}).get('favorites', {})
        if not favorites_config:
            raise self.NoSuchProfileException(profile_config['name'])

        args: dict[str, Any] = {
            'token_infos': {
                'xivo_user_uuid': user_uuid
            },  # To avoid breaking old plugins
            'token': token,
            'xivo_user_uuid': user_uuid,  # To avoid breaking old plugins
            'user_uuid': user_uuid,
        }
        futures: list[Future[list[_SourceResult]]] = []
        favorite_map = self.favorite_ids(profile_config, user_uuid).by_uuid
        for source_uuid, ids in favorite_map.items():
            source = self._source_manager.get(source_uuid)
            if not source:
                continue
            futures.append(self._async_list(source, ids, args))

        params: dict[str, Any] = {'return_when': ALL_COMPLETED}
        if 'lookup_timeout' in self._config:
            params['timeout'] = self._config['lookup_timeout']

        done, _ = wait(futures, **params)
        results: list[_SourceResult] = []
        for future in done:
            for result in future.result():
                results.append(result)
        return results

    def favorite_ids(self, profile_config: ProfileConfig, user_uuid: str) -> Any:
        favorites = self._crud.get(user_uuid)
        favorite_config = profile_config.get('services', {}).get('favorites', {})
        enabled_sources: dict[str, SourceConfig] = {
            source['name']: source for source in favorite_config.get('sources', [])
        }

        by_uuid: defaultdict[str, list[str]] = defaultdict(list)
        by_name: defaultdict[str, list[str]] = defaultdict(list)
        for name, id_ in favorites:
            source = enabled_sources.get(name)
            if not source:
                continue
            by_uuid[source['uuid']].append(id_)
            by_name[source['name']].append(id_)

        FavoriteList = namedtuple('FavoriteList', ['by_uuid', 'by_name'])
        return FavoriteList(by_uuid, by_name)

    def new_favorite(
        self,
        tenant_uuid: str,
        source_name: str,
        contact_id: str,
        user_uuid: str,
    ) -> None:
        sources = self._available_sources(tenant_uuid)
        matching_source = None
        for source in sources:
            if source['name'] == source_name:
                matching_source = source
                break

        if not matching_source:
            raise self.NoSuchSourceException(source_name)

        backend = source['backend']
        self._crud.create(user_uuid, tenant_uuid, backend, source_name, contact_id)
        event = FavoriteAddedEvent(
            source_name, contact_id, self._xivo_uuid, tenant_uuid, user_uuid
        )
        self._bus.publish(event)

    def remove_favorite(
        self,
        tenant_uuid: str,
        source_name: str,
        contact_id: str,
        user_uuid: str,
    ) -> None:
        sources = self._available_sources(tenant_uuid)
        matching_source = None
        for source in sources:
            if source['name'] == source_name:
                matching_source = source
                break

        if not matching_source:
            raise self.NoSuchSourceException(source_name)

        self._crud.delete(user_uuid, source_name, contact_id)
        event = FavoriteDeletedEvent(
            source_name, contact_id, self._xivo_uuid, tenant_uuid, user_uuid
        )
        self._bus.publish(event)
