# Copyright 2015-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed

from wazo_dird import BaseServicePlugin, helpers

logger = logging.getLogger(__name__)


class ReverseServicePlugin(BaseServicePlugin):
    def __init__(self):
        self._service = None

    def load(self, dependencies):
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

    def unload(self):
        if self._service:
            self._service.stop()
            self._service = None


class _ReverseService(helpers.BaseService):
    _service_name = 'reverse'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._executor = ThreadPoolExecutor(max_workers=10)

    def stop(self):
        self._executor.shutdown()

    def reverse_many(
        self, profile_config, extens, profile, args=None, user_uuid=None, token=None
    ):
        args = args or {}
        futures = []
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
        timeout = (service_config.get('options') or {}).get('timeout') or 1

        results = {exten: None for exten in extens}
        try:
            for future in as_completed(futures, timeout=timeout):
                if result := future.result():
                    results.update(result)
                    if all(result is not None for result in results.values()):
                        pending_futures = [
                            future for future in futures if not future.done()
                        ]
                        cancelled_futures = sum(
                            1 for future in pending_futures if future.cancel()
                        )
                        logger.debug(
                            'Cancelled %d/%d pending reverse lookup tasks',
                            cancelled_futures,
                            len(pending_futures),
                        )
                        break
        except TimeoutError:
            logger.warning(
                'Timeout on reverse many lookup, returning partial results (extens=%s)',
                extens,
            )
            cancelled_futures = 0
            for future in futures:
                if not future.done() and future.cancel():
                    cancelled_futures += 1
            logger.debug(
                'Timeout: cancelled %d/%d reverse lookup tasks',
                cancelled_futures,
                len(futures),
            )
        return [value for value in results.values()]

    def _async_reverse_many(self, source, extens, args):
        raise_stopper = helpers.RaiseStopper(return_on_raise=None)
        future = self._executor.submit(
            raise_stopper.execute, source.match_all, extens, args
        )
        future.name = source.name
        return future

    def reverse(
        self, profile_config, exten, profile, args=None, user_uuid=None, token=None
    ):
        args = args or {}
        futures = []
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
        timeout = (service_config.get('options') or {}).get('timeout') or 1

        try:
            for future in as_completed(futures, timeout=timeout):
                if result := future.result():
                    pending_futures = [f for f in futures if not f.done()]
                    cancelled_futures = sum(1 for f in pending_futures if f.cancel())
                    logger.debug(
                        'Cancelled %d/%d pending reverse lookup tasks',
                        cancelled_futures,
                        len(pending_futures),
                    )
                    return result
        except TimeoutError:
            logger.warning('Timeout on reverse lookup for exten: %s', exten)
            cancelled_futures = sum(1 for f in futures if not f.done() and f.cancel())
            logger.debug(
                'cancelled %d/%d reverse lookup tasks', cancelled_futures, len(futures)
            )

    def _async_reverse(self, source, exten, args):
        raise_stopper = helpers.RaiseStopper(return_on_raise=None)
        future = self._executor.submit(
            raise_stopper.execute, source.first_match, exten, args
        )
        future.name = source.name
        return future
