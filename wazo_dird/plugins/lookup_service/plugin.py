# Copyright 2014-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ALL_COMPLETED, Future, ThreadPoolExecutor, wait
from time import perf_counter
from typing import Any, NamedTuple, TypeVar

from wazo_dird import BaseServicePlugin, BaseSourcePlugin, helpers
from wazo_dird.contacts_cache import ContactsCache
from wazo_dird.helpers import ProfileConfig
from wazo_dird.plugin_manager import ServiceDependencies
from wazo_dird.plugins.base_plugins import LookupArgs
from wazo_dird.plugins.source_result import _SourceResult as SourceResult

from . import sorted_index
from .sorted_index import Member, TenantSortedIndex

logger = logging.getLogger(__name__)
timing_logger = logger.getChild('timing')

T = TypeVar('T')

# The services whose sources a tenant's contact list gathers
LISTED_SERVICES = ('lookup', 'reverse', 'favorites')
DEFAULT_CONTACTS_LIST = {'timeout': 10, 'cache_ttl': 30, 'cache_max_contacts': 100_000}


class ContactListing(NamedTuple):
    # The cacheable sources whose list is stored, by source uuid
    shared: dict[str, Member]
    # The other sources' contacts, read for this request only
    fresh: list[SourceResult]
    # The names of the sources that failed or timed out
    missing_sources: list[str]
    # False when a cacheable source failed, timed out or was not stored: the
    # shared list then misses a member and must not be stored
    shared_complete: bool


class ContactPage(NamedTuple):
    items: list[SourceResult]
    total: int
    missing_sources: list[str]


def _returning_errors(function: Callable[..., T], *args: Any) -> T | Exception:
    # Unlike RaiseStopper, keeps the failure so the source is named missing
    try:
        return function(*args)
    except Exception as e:
        logger.warning('listing failed: %s', e)
        logger.debug('listing failure', exc_info=True)
        return e


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

        list_config = {**DEFAULT_CONTACTS_LIST, **self._config.get('contacts_list', {})}
        self._list_timeout: float = list_config['timeout']
        self._list_cache: ContactsCache[SourceResult] | None = None
        self._sorted_index: TenantSortedIndex | None = None
        if list_config['cache_ttl']:
            self._list_cache = ContactsCache(
                list_config['cache_ttl'],
                list_config['cache_max_contacts'],
                self._list_timeout,
            )
            self._sorted_index = TenantSortedIndex(list_config['cache_ttl'])
            self._source_manager.subscribe_invalidate(self._forget_source)

    def stop(self) -> None:
        self._executor.shutdown()

    def _forget_source(self, source_uuid: str) -> None:
        assert self._list_cache and self._sorted_index
        self._list_cache.evict(source_uuid)
        self._sorted_index.forget_source(source_uuid)

    def _async_search(
        self, source: BaseSourcePlugin, term: str, args: LookupArgs
    ) -> Future[helpers.TimedResult[list[SourceResult]]]:
        raise_stopper: helpers.RaiseStopper[list[SourceResult]] = helpers.RaiseStopper(
            return_on_raise=[]
        )
        return self._submit(source, raise_stopper.execute, source.search, term, args)

    def _submit(
        self, source: BaseSourcePlugin, function: Callable[..., T], *args: Any
    ) -> Future[helpers.TimedResult[T]]:
        future = self._executor.submit(
            helpers.timed, perf_counter(), function, *args
        )
        setattr(future, 'name', source.name)
        return future

    def _list_source(
        self, source_uuid: str, source: BaseSourcePlugin, args: LookupArgs
    ) -> tuple[int | None, list[SourceResult]]:
        if self._list_cache is not None and source.list_cacheable:
            return self._list_cache.get_or_fetch_versioned(
                source_uuid, lambda: source.list_all(args)
            )
        return None, source.list_all(args)

    def list_all(
        self,
        profile_configs: list[ProfileConfig],
        user_uuid: str | None,
        token: str | None,
    ) -> ContactListing:
        """Every contact of the sources of the profiles' listed services, each
        source listed once, waiting contacts_list.timeout at most"""
        args = LookupArgs(token=token, user_uuid=user_uuid, xivo_user_uuid=user_uuid)
        sources: dict[str, BaseSourcePlugin] = {}
        for profile_config in profile_configs:
            for service_name in LISTED_SERVICES:
                for uuid, source in self._sources_of(profile_config, service_name):
                    sources.setdefault(uuid, source)

        futures = {
            self._submit(
                source, _returning_errors, self._list_source, uuid, source, args
            ): (uuid, source)
            for uuid, source in sources.items()
        }
        done, not_done = (
            wait(futures, timeout=self._list_timeout, return_when=ALL_COMPLETED)
            if futures
            else (set(), set())
        )

        shared: dict[str, Member] = {}
        fresh: list[SourceResult] = []
        missing: list[str] = []
        shared_complete = True
        backend_stats: list[helpers.BackendStat] = []
        for future in done:
            uuid, source = futures[future]
            outcome, timing = future.result()
            if isinstance(outcome, Exception):
                missing.append(source.name)
                shared_complete = shared_complete and not source.list_cacheable
                backend_stats.append(helpers.BackendStat.finished(source.name, 0, timing))
                continue
            version, contacts = outcome
            backend_stats.append(
                helpers.BackendStat.finished(source.name, len(contacts), timing)
            )
            if version is None:
                fresh.extend(contacts)
                shared_complete = shared_complete and not (
                    self._list_cache is not None and source.list_cacheable
                )
            else:
                shared[uuid] = (version, contacts)
        for future in not_done:
            future.cancel()
            source = futures[future][1]
            missing.append(source.name)
            shared_complete = shared_complete and not source.list_cacheable
        backend_stats.extend(helpers.BackendStat.from_future(f) for f in not_done)
        helpers.log_backend_stats(timing_logger, 'list_all', backend_stats)
        return ContactListing(shared, fresh, sorted(missing), shared_complete)

    def list_page(
        self,
        profile_configs: list[ProfileConfig],
        tenant_uuid: str,
        user_uuid: str | None,
        token: str | None,
        limit: int,
        offset: int,
    ) -> ContactPage:
        """One page of the tenant's contacts, by source name then contact id"""
        listing = self.list_all(profile_configs, user_uuid, token)
        if self._sorted_index is not None and listing.shared_complete:
            shared = self._sorted_index.get(tenant_uuid, listing.shared)
        else:
            # Not stored: the next page lists the missing sources again
            shared = sorted_index.build_sorted(
                contacts for _, contacts in listing.shared.values()
            )
        items = sorted_index.page_by_rank(shared, listing.fresh, offset, limit)
        total = len(shared.results) + len(listing.fresh)
        return ContactPage(items, total, listing.missing_sources)

    def lookup(
        self,
        profile_config: ProfileConfig,
        tenant_uuid: str,
        term: str,
        user_uuid: str | None,
        token: str | None = None,
    ) -> list[SourceResult]:
        args = LookupArgs(token=token, user_uuid=user_uuid, xivo_user_uuid=user_uuid)
        futures = [
            self._async_search(source, term, args)
            for source in self.source_from_profile(profile_config)
        ]

        params: dict[str, Any] = {'return_when': ALL_COMPLETED}
        service_config = self.get_service_config(profile_config)
        timeout = (service_config.get('options') or {}).get('timeout')
        if timeout:
            params['timeout'] = timeout

        done, not_done = wait(futures, **params)
        results = []
        backend_stats: list[helpers.BackendStat] = []
        for future in done:
            contacts, timing = future.result()
            backend_stats.append(
                helpers.BackendStat.finished(
                    getattr(future, 'name'), len(contacts), timing
                )
            )
            results.extend(contacts)
        backend_stats.extend(helpers.BackendStat.from_future(f) for f in not_done)
        helpers.log_backend_stats(timing_logger, 'lookup', backend_stats)
        return results
