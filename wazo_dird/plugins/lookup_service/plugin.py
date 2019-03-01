# Copyright 2014-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from concurrent.futures import ALL_COMPLETED
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait
from wazo_dird import BaseServicePlugin
from wazo_dird import helpers

logger = logging.getLogger(__name__)


class LookupServicePlugin(BaseServicePlugin):

    def __init__(self):
        self._service = None

    def load(self, dependencies):
        try:
            self._service = _LookupService(
                dependencies['config'],
                dependencies['source_manager'],
                dependencies['controller'],
            )
            return self._service
        except KeyError:
            msg = ('%s should be loaded with "config" and "source_manager" but received: %s'
                   % (self.__class__.__name__, ','.join(dependencies.keys())))
            raise ValueError(msg)

    def unload(self):
        if self._service:
            self._service.stop()
            self._service = None


class _LookupService(helpers.BaseService):

    _service_name = 'lookup'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._executor = ThreadPoolExecutor(max_workers=10)

    def stop(self):
        self._executor.shutdown()

    def _async_search(self, source, term, args):
        raise_stopper = helpers.RaiseStopper(return_on_raise=[])
        future = self._executor.submit(raise_stopper.execute, source.search, term, args)
        future.name = source.name
        return future

    def lookup(self, profile_config, tenant_uuid, term, xivo_user_uuid, args=None, token=None):
        args = args or {}
        futures = []
        sources = self.source_from_profile(profile_config)
        for source in sources:
            args['token'] = token
            args['xivo_user_uuid'] = xivo_user_uuid
            futures.append(self._async_search(source, term, args))

        params = {'return_when': ALL_COMPLETED}
        service_config = self.get_service_config(profile_config)
        timeout = service_config.get('timeout')
        if timeout:
            params['timeout'] = timeout

        done, _ = wait(futures, **params)
        results = []
        for future in done:
            for result in future.result():
                results.append(result)
        return results
