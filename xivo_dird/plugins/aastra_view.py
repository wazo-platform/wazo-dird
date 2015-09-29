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


import os
import logging

from jinja2 import FileSystemLoader
from jinja2 import Environment

from xivo_dird import BaseViewPlugin
from xivo_dird.core.rest_api import api
from xivo_dird.plugins.phone_helpers import new_phone_display_from_config
from xivo_dird.plugins.phone_view import PhoneInput, PhoneLookup

logger = logging.getLogger(__name__)

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_FOLDER = os.path.join(CURRENT_PATH, 'lookup_templates')
TEMPLATE_AASTRA_INPUT = "aastra_input.jinja"
TEMPLATE_AASTRA_RESULTS = "aastra_results.jinja"

CONTENT_TYPE = 'text/xml'
MAX_ITEM_PER_PAGE = 16


class AastraViewPlugin(BaseViewPlugin):

    aastra_input = '/directories/input/<profile>/aastra'
    aastra_lookup = '/directories/lookup/<profile>/aastra'

    def load(self, args=None):
        phone_display = new_phone_display_from_config(args['config'])
        jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_FOLDER))
        template_input = jinja_env.get_template(TEMPLATE_AASTRA_INPUT)
        template_lookup = jinja_env.get_template(TEMPLATE_AASTRA_RESULTS)

        lookup_service = args['services'].get('lookup')
        if lookup_service:
            PhoneInput.configure(lookup_service)
            PhoneLookup.configure(lookup_service, phone_display)
            api.add_resource(PhoneInput, self.aastra_input, endpoint='AastraPhoneInput',
                             resource_class_args=(template_input, CONTENT_TYPE))
            api.add_resource(PhoneLookup, self.aastra_lookup, endpoint='AastraPhoneLookup',
                             resource_class_args=(template_lookup, CONTENT_TYPE, MAX_ITEM_PER_PAGE))
