# Copyright 2014-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from concurrent.futures import ALL_COMPLETED, Future, ThreadPoolExecutor, wait
from time import perf_counter
from typing import Any

from wazo_dird import BaseServicePlugin, BaseSourcePlugin, helpers
from wazo_dird.helpers import ProfileConfig
from wazo_dird.plugin_manager import ServiceDependencies
from wazo_dird.plugins.source_result import _SourceResult as SourceResult

logger = logging.getLogger(__name__)
timing_logger = logger.getChild('timing')


class LookupServicePlugin(BaseServicePlugin):
    def __init__(self) -> None:
        self._service: _LookupService | None = None

    def load(self, dependencies: ServiceDependencies) -> _LookupService:
        try:
            self._service = _LookupService(
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


class _LookupService(helpers.BaseService):
    _service_name = 'lookup'

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        http_threads = self._config.get('rest_api', {}).get('max_threads', 10)
        executor_workers = self._config.get('lookup_service', {}).get(
            'executor_workers'
        )
        max_workers = executor_workers if executor_workers is not None else http_threads
        logger.info('Creating Lookup service threadpool [max_workers=%d]', max_workers)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def stop(self) -> None:
        self._executor.shutdown()

    def _async_search(
        self, source: BaseSourcePlugin, term: str, args: dict[str, Any]
    ) -> Future[list[SourceResult]]:
        raise_stopper: helpers.RaiseStopper[list[SourceResult]] = helpers.RaiseStopper(
            return_on_raise=[]
        )
        submitted_at = perf_counter()
        future = self._executor.submit(
            self._timed_search, raise_stopper, source, term, args, submitted_at
        )
        setattr(future, 'name', source.name)
        return future

    def _timed_search(
        self,
        raise_stopper: helpers.RaiseStopper[list[SourceResult]],
        source: BaseSourcePlugin,
        term: str,
        args: dict[str, Any],
        submitted_at: float,
    ) -> list[SourceResult]:
        started_at = perf_counter()
        results = raise_stopper.execute(source.search, term, args)
        finished_at = perf_counter()
        timing_logger.debug(
            'lookup source=%s backend=%s queue_ms=%.1f exec_ms=%.1f results=%d',
            source.name,
            source.backend,
            (started_at - submitted_at) * 1000,
            (finished_at - started_at) * 1000,
            len(results),
        )
        return results

    def lookup(
        self,
        profile_config: ProfileConfig,
        tenant_uuid: str,
        term: str,
        user_uuid: str | None,
        args: dict[str, Any] | None = None,
        token: str | None = None,
    ) -> list[SourceResult]:
        args = args or {}
        futures = []
        sources = self.source_from_profile(profile_config)
        for source in sources:
            args['token'] = token
            args['user_uuid'] = user_uuid
            args['xivo_user_uuid'] = user_uuid
            futures.append(self._async_search(source, term, args))

        params: dict[str, Any] = {'return_when': ALL_COMPLETED}
        service_config = self.get_service_config(profile_config)
        timeout = (service_config.get('options') or {}).get('timeout')
        if timeout:
            params['timeout'] = timeout

        done, _ = wait(futures, **params)
        results = []
        for future in done:
            for result in future.result():
                results.append(result)
        return results
