# -*- coding: utf-8 -*-
#
# Copyright 2014-2017 The Wazo Authors  (see the AUTHORS file)
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

from concurrent.futures import ALL_COMPLETED
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait
from xivo_dird import BaseServicePlugin
from xivo_dird import helpers

logger = logging.getLogger(__name__)


class LookupServicePlugin(BaseServicePlugin):

    def __init__(self):
        self._service = None

    def load(self, args):
        try:
            self._service = _LookupService(args['config'], args['sources'])
            return self._service
        except KeyError:
            msg = ('%s should be loaded with "config" and "sources" but received: %s'
                   % (self.__class__.__name__, ','.join(args.keys())))
            raise ValueError(msg)

    def unload(self):
        if self._service:
            self._service.stop()
            self._service = None


class _LookupService(helpers.BaseService):

    _service_name = 'lookup'

    def __init__(self, *args, **kwargs):
        super(_LookupService, self).__init__(*args, **kwargs)
        self._executor = ThreadPoolExecutor(max_workers=10)

    def stop(self):
        self._executor.shutdown()

    def _async_search(self, source, term, args):
        raise_stopper = helpers.RaiseStopper(return_on_raise=[])
        future = self._executor.submit(raise_stopper.execute, source.search, term, args)
        future.name = source.name
        return future

    def lookup(self, term, profile, xivo_user_uuid, args=None, token=None):
        args = args or {}
        futures = []
        for source in self.source_by_profile(profile):
            args['token'] = token
            args['xivo_user_uuid'] = xivo_user_uuid
            futures.append(self._async_search(source, term, args))

        params = {'return_when': ALL_COMPLETED}
        if 'timeout' in self.config_by_profile(profile):
            params['timeout'] = self.config_by_profile(profile)['timeout']

        done, _ = wait(futures, **params)
        results = []
        for future in done:
            for result in future.result():
                results.append(result)
        return results
