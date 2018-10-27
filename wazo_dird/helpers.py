# -*- coding: utf-8 -*-
# Copyright 2015-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

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

        for name, enabled in sources.items():
            if not enabled or name not in self._sources:
                continue
            result.append(self._sources[name])

        if not result:
            logger.warning('Cannot find "%s" sources for profile %s', self._service_name, profile)

        return result
