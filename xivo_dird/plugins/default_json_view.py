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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import logging

from functools import partial
from xivo_dird import BaseViewPlugin

logger = logging.getLogger(__name__)


class JsonViewPlugin(BaseViewPlugin):

    API_VERSION = '0.1'
    ROUTE = '/{version}/directories/lookup/<profile>'.format(version=API_VERSION)

    def load(self, args=None):
        if not args:
            args = {}

        if 'http_app' not in args:
            logger.error('HTTP view loaded with an http_app')
            return

        lookup_fn = partial(_lookup, args.get('services', {}))
        args['http_app'].add_url_rule(self.ROUTE, __name__, lookup_fn)


def _lookup(services, profile):
    pass
