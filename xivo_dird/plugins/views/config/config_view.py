# -*- coding: utf-8 -*-
#
# Copyright 2016-2017 The Wazo Authors  (see the AUTHORS file)
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

from xivo_dird import BaseViewPlugin
from xivo_dird.auth import required_acl
from xivo_dird.rest_api import api, AuthResource


logger = logging.getLogger(__name__)


class ConfigViewPlugin(BaseViewPlugin):

    url = '/config'

    def load(self, args):
        config_service = args['services'].get('config')
        if not config_service:
            logger.info('failed to load the %s config service is disabled', self.__class__.__name__)
            return

        Config.configure(config_service)

        api.add_resource(Config, self.url)


class Config(AuthResource):

    _config_service = None

    @classmethod
    def configure(cls, config_service):
        cls._config_service = config_service

    @required_acl('dird.config.read')
    def get(self):
        config = self._config_service.get_current_config()
        return dict(config)
