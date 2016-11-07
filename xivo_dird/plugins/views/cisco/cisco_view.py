# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Avencall
# Copyright (C) 2016 Proformatique, Inc.
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

from xivo_dird import BaseViewPlugin
from xivo_dird.core.rest_api import api
from xivo_dird.plugins.phone_helpers import new_phone_lookup_service_from_args
from xivo_dird.plugins.views.phone.phone_view import PhoneMenu, PhoneInput, PhoneLookup

TEMPLATE_CISCO_MENU = "cisco_menu.jinja"
TEMPLATE_CISCO_INPUT = "cisco_input.jinja"
TEMPLATE_CISCO_RESULTS = "cisco_results.jinja"

CONTENT_TYPE = 'text/xml'
MAX_ITEM_PER_PAGE = 16


class CiscoViewPlugin(BaseViewPlugin):

    cisco_menu = '/directories/menu/<profile>/<xivo_user_uuid>/cisco'
    cisco_input = '/directories/input/<profile>/<xivo_user_uuid>/cisco'
    cisco_lookup = '/directories/lookup/<profile>/<xivo_user_uuid>/cisco'

    def load(self, args=None):
        phone_lookup_service = new_phone_lookup_service_from_args(args)
        api.add_resource(PhoneMenu, self.cisco_menu, endpoint='CiscoPhoneMenu',
                         resource_class_args=(TEMPLATE_CISCO_MENU, CONTENT_TYPE))
        api.add_resource(PhoneInput, self.cisco_input, endpoint='CiscoPhoneInput',
                         resource_class_args=(TEMPLATE_CISCO_INPUT, CONTENT_TYPE))
        api.add_resource(PhoneLookup, self.cisco_lookup, endpoint='CiscoPhoneLookup',
                         resource_class_args=(TEMPLATE_CISCO_RESULTS, CONTENT_TYPE,
                                              phone_lookup_service, MAX_ITEM_PER_PAGE))
