# Copyright 2015-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError
from concurrent.futures import as_completed
from wazo_dird import BaseServicePlugin
from wazo_dird import helpers

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

        params = {}
        service_config = self.get_service_config(profile_config)
        timeout = service_config.get('timeout')
        if timeout:
            params['timeout'] = timeout

        results = {exten: None for exten in extens}
        try:
            for future in as_completed(futures, **params):
                if future.result():
                    results.update(future.result())
                    if all(result is not None for result in results.values()):
                        for other_future in futures:
                            other_future.cancel()
                        break
        except TimeoutError:
            logger.info('Timeout on reverse many lookup for extens: %s', extens)
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

        params = {}
        service_config = self.get_service_config(profile_config)
        timeout = service_config.get('timeout')
        if timeout:
            params['timeout'] = timeout

        try:
            for future in as_completed(futures, **params):
                if future.result() is not None:
                    for other_future in futures:
                        other_future.cancel()
                    return future.result()
        except TimeoutError:
            logger.info('Timeout on reverse lookup for exten: %s', exten)

    def _async_reverse(self, source, exten, args):
        raise_stopper = helpers.RaiseStopper(return_on_raise=None)
        future = self._executor.submit(
            raise_stopper.execute, source.first_match, exten, args
        )
        future.name = source.name
        return future
