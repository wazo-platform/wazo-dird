# Copyright 2015-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

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

    def load(self, args):
        try:
            self._service = _ReverseService(args['config'], args['sources'])
            return self._service
        except KeyError:
            msg = ('%s should be loaded with "config" and "sources" but received: %s'
                   % (self.__class__.__name__, ','.join(args.keys())))
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

    def reverse(self, exten, profile, args=None, xivo_user_uuid=None, token=None):
        args = args or {}
        futures = []
        sources = self.source_by_profile(profile)
        logger.debug('Reverse lookup for {} in sources {}'.format(exten, [source.name for source in sources]))
        for source in sources:
            args['token'] = token
            args['xivo_user_uuid'] = xivo_user_uuid
            futures.append(self._async_reverse(source, exten, args))

        params = {}
        if 'timeout' in self.config_by_profile(profile):
            params['timeout'] = self.config_by_profile(profile)['timeout']

        try:
            for future in as_completed(futures, **params):
                if future.result() is not None:
                    for other_future in futures:
                        other_future.cancel()
                    return future.result()
        except TimeoutError:
            logger.info('Timeout on reverse lookup for exten: %s', exten)

    def _async_reverse(self, source, exten, args):
        raise_stopper = helpers.RaiseStopper(return_on_raise=[])
        future = self._executor.submit(raise_stopper.execute, source.first_match, exten, args)
        future.name = source.name
        return future
