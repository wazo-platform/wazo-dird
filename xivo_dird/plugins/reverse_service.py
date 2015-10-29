# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import logging

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from xivo_dird import BaseServicePlugin
from xivo_dird import helpers

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


class _ReverseService(object):

    def __init__(self, config, sources):
        self._global_config = config
        self._sources = sources
        self._executor = ThreadPoolExecutor(max_workers=10)

    def stop(self):
        self._executor.shutdown()

    def reverse(self, exten, profile, args, token_infos):
        futures = []
        for source in self._source_by_profile(profile):
            args['token_infos'] = token_infos
            futures.append(self._async_reverse(source, exten, args))

        params = {}
        if 'timeout' in self._config(profile):
            params['timeout'] = self._config(profile)['timeout']

        for future in as_completed(futures, **params):
            if future.result() is not None:
                for other_future in futures:
                    other_future.cancel()
                return future.result()
        return None

    def _config(self, profile):
        return self._global_config.get('services', {}).get('reverse', {}).get(profile, {})

    def _async_reverse(self, source, exten, args):
        raise_stopper = helpers.RaiseStopper(return_on_raise=[])
        future = self._executor.submit(raise_stopper.execute, source.first_match, exten, args)
        future.name = source.name
        return future

    def _source_by_profile(self, profile):
        try:
            source_names = self._config(profile)['sources']
        except KeyError:
            logger.warning('Cannot find reverse sources for profile %s', profile)
            return []
        else:
            return [self._sources[name] for name in source_names if name in self._sources]
