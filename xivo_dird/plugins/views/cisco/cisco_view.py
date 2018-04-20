# -*- coding: utf-8 -*-
# Copyright 2015-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo_dird import BaseViewPlugin
from xivo_dird.rest_api import api
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
