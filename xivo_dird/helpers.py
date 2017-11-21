# -*- coding: utf-8 -*-
#
# Copyright 2015-2017 The Wazo Authors  (see the AUTHORS file)
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

logger = logging.getLogger()


class RaiseStopper(object):

    def __init__(self, return_on_raise):
        self.return_on_raise = return_on_raise

    def execute(self, function, *args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception:
            logger.exception('An error occured in %s', function.__name__)
        return self.return_on_raise


class BaseService(object):

    def __init__(self, config, sources, *args, **kwargs):
        self._config = config
        self._sources = sources

    def config_by_profile(self, profile):
        return self._config.get('services', {}).get(self._service_name, {}).get(profile, {})

    def source_by_profile(self, profile):
        sources = self.config_by_profile(profile).get('sources', {})
        result = []

        for name, enabled in sources.iteritems():
            if not enabled or name not in self._sources:
                continue
            result.append(self._sources[name])

        if not result:
            logger.warning('Cannot find "%s" sources for profile %s', self._service_name, profile)

        return result
