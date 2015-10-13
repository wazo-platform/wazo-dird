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
from xivo_dird.plugins.phone_view import PhoneInput, PhoneLookup

logger = logging.getLogger(__name__)

TEMPLATE_POLYCOM_INPUT = "polycom_input.jinja"
TEMPLATE_POLYCOM_RESULTS = "polycom_results.jinja"

CONTENT_TYPE = 'text/html; charset=UTF-8'
MAX_ITEM_PER_PAGE = 16


class PolycomViewPlugin(BaseViewPlugin):

    polycom_input = '/directories/input/<profile>/polycom'
    polycom_lookup = '/directories/lookup/<profile>/polycom'

    def load(self, args=None):
        phone_display = new_phone_display_from_config(args['config'])
        lookup_service = args['services'].get('lookup')
        if lookup_service:
            PhoneLookup.configure(lookup_service, phone_display)
            api.add_resource(PhoneInput, self.polycom_input, endpoint='PolycomPhoneInput',
                             resource_class_args=(TEMPLATE_POLYCOM_INPUT, CONTENT_TYPE))
            api.add_resource(PhoneLookup, self.polycom_lookup, endpoint='PolycomPhoneLookup',
                             resource_class_args=(TEMPLATE_POLYCOM_RESULTS, CONTENT_TYPE, MAX_ITEM_PER_PAGE))
