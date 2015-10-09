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

from xivo_dird import BaseViewPlugin
from xivo_dird.core.rest_api import api
from xivo_dird.plugins.phone_helpers import new_phone_display_from_config
from xivo_dird.plugins.phone_view import PhoneLookup

logger = logging.getLogger(__name__)

TEMPLATE_YEALINK_RESULTS = "yealink_results.jinja"

CONTENT_TYPE = 'text/xml'


class YealinkViewPlugin(BaseViewPlugin):

    yealink_lookup = '/directories/lookup/<profile>/yealink'

    def load(self, args=None):
        phone_display = new_phone_display_from_config(args['config'])
        lookup_service = args['services'].get('lookup')
        if lookup_service:
            PhoneLookup.configure(lookup_service, phone_display)
            api.add_resource(PhoneLookup, self.yealink_lookup, endpoint='YealinkPhoneLookup',
                             resource_class_args=(TEMPLATE_YEALINK_RESULTS, CONTENT_TYPE))