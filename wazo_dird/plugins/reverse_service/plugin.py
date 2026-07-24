# Copyright 2015-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError, as_completed
from typing import Any

from wazo_dird import BaseServicePlugin, BaseSourcePlugin, helpers
from wazo_dird.helpers import ProfileConfig
from wazo_dird.plugin_manager import ServiceDependencies
from wazo_dird.plugins.source_result import _SourceResult as SourceResult

logger = logging.getLogger(__name__)


class ReverseServicePlugin(BaseServicePlugin):
    def __init__(self) -> None:
        self._service: _ReverseService | None = None

    def load(self, dependencies: ServiceDependencies) -> _ReverseService:
        try:
            self._service = _ReverseService(
                dependencies['config'],
                dependencies['source_manager'],
                dependencies['controller'],
            )
            return self._service
        except KeyError:
            msg = (
                '%s should be loaded with "config" and "source_manager" but received: %s'
                % (self.__class__.__name__, ','.join(dependencies.keys()))
            )
            raise ValueError(msg)

    def unload(self) -> None:
        if self._service:
            self._service.stop()
            self._service = None


class _ReverseService(helpers.BaseService):
    _service_name = 'reverse'

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        http_threads = self._config.get('rest_api', {}).get('max_threads', 10)
        executor_workers = self._config.get('reverse_service', {}).get(
            'executor_workers'
        )
        max_workers = executor_workers if executor_workers is not None else http_threads
        logger.info('Creating reverse service threadpool [max_workers=%d]', max_workers)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def stop(self) -> None:
        self._executor.shutdown()

    @staticmethod
    def _cancel_pending(futures: list[Future]) -> None:
        pending = [f for f in futures if not f.done()]
        cancelled = sum(1 for f in pending if f.cancel())
        logger.debug(
            'Cancelled %d/%d pending reverse lookup tasks', cancelled, len(pending)
        )

    def reverse_many(
        self,
        profile_config: ProfileConfig,
        extens: list[str],
        profile: str,
        args: dict[str, Any] | None = None,
        user_uuid: str | None = None,
        token: str | None = None,
    ) -> list[SourceResult | None]:
        args = args or {}
        futures: list[Future[dict[str, SourceResult] | None]] = []
        sources = self.source_from_profile(profile_config)
        logger.debug(
            'Reverse lookup for %s in sources %s',
            extens,
            [source.name for source in sources],
        )
        for source in sources:
            args['token'] = token
            args['user_uuid'] = user_uuid
            # To avoid breaking plugins which used the xivo_user_uuid and reverse fallback
            args['xivo_user_uuid'] = user_uuid
            futures.append(self._async_reverse_many(source, extens, args))

        service_config = self.get_service_config(profile_config)
        timeout: float | None = (service_config.get('options') or {}).get(
            'timeout'
        ) or 1

        results: dict[str, SourceResult | None] = {exten: None for exten in extens}
        completed_sources = set()
        try:
            for future in as_completed(futures, timeout=timeout):
                completed_sources.add(getattr(future, 'name'))
                if result := future.result():
                    results.update(result)
                    if all(result is not None for result in results.values()):
                        self._cancel_pending(futures)
                        break
        except TimeoutError:
            incomplete_matches = [
                getattr(future, 'name')
                for future in futures
                if getattr(future, 'name') not in completed_sources
            ]
            logger.warning(
                'Timeout on reverse many lookup, returning partial results (extens=%s, incomplete=%s)',
                extens,
                incomplete_matches,
            )
            self._cancel_pending(futures)
        return [value for value in results.values()]

    def _async_reverse_many(
        self, source: BaseSourcePlugin, extens: list[str], args: dict[str, Any]
    ) -> Future[dict[str, SourceResult] | None]:
        raise_stopper: helpers.RaiseStopper[
            dict[str, SourceResult] | None
        ] = helpers.RaiseStopper(return_on_raise=None)
        future = self._executor.submit(
            raise_stopper.execute, source.match_all, extens, args
        )
        setattr(future, 'name', source.name)
        return future

    def reverse(
        self,
        profile_config: ProfileConfig,
        exten: str,
        profile: str,
        args: dict[str, Any] | None = None,
        user_uuid: str | None = None,
        token: str | None = None,
    ) -> SourceResult | None:
        args = args or {}
        futures: list[Future[SourceResult | None]] = []
        sources = self.source_from_profile(profile_config)
        logger.debug(
            'Reverse lookup for %s in sources %s',
            exten,
            [source.name for source in sources],
        )
        for source in sources:
            args['token'] = token
            args['user_uuid'] = user_uuid
            # To avoid breaking plugins which used the xivo_user_uuid
            args['xivo_user_uuid'] = user_uuid
            futures.append(self._async_reverse(source, exten, args))

        service_config = self.get_service_config(profile_config)
        timeout: float | None = (service_config.get('options') or {}).get(
            'timeout'
        ) or 1

        completed_sources = set()
        try:
            for future in as_completed(futures, timeout=timeout):
                completed_sources.add(getattr(future, 'name'))
                if result := future.result():
                    self._cancel_pending(futures)
                    return result
        except TimeoutError:
            incomplete_matches = [
                getattr(future, 'name')
                for future in futures
                if getattr(future, 'name') not in completed_sources
            ]
            logger.warning(
                'Timeout on reverse lookup for exten: %s, incomplete=%s',
                exten,
                incomplete_matches,
            )
            self._cancel_pending(futures)

    def _async_reverse(
        self, source: BaseSourcePlugin, exten: str, args: dict[str, Any]
    ) -> Future[SourceResult | None]:
        raise_stopper: helpers.RaiseStopper[SourceResult | None] = helpers.RaiseStopper(
            return_on_raise=None
        )
        future = self._executor.submit(
            raise_stopper.execute, source.first_match, exten, args
        )
        setattr(future, 'name', source.name)
        return future
