# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import logging

from xivo import wsgi
from xivo_dird.core.rest_api import CoreRestApi

logger = logging.getLogger(__name__)


class Controller(object):
    def __init__(self):
        self.config = {
            'log_filename': '/var/log/xivo-dird.log',
            'foreground': True,
            'user': 'www-data',
            'pid_filename': '/var/run/xivo-dird/xivo-dird.pid',
            'rest_api': {
                'static_folder': '/usr/share/xivo-dird/static'
            }
        }
        self.rest_api = CoreRestApi(self.config['rest_api'])

    def run(self):
        logger.info('xivo-dird running...')
        wsgi.run(self.rest_api.app)
