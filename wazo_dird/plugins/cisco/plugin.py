# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import BaseViewPlugin
from wazo_dird.plugins.phone_helpers import new_phone_lookup_service_from_args
from wazo_dird.plugins.phone.http import PhoneMenu, PhoneInput, PhoneLookup

TEMPLATE_CISCO_MENU = "cisco_menu.jinja"
TEMPLATE_CISCO_INPUT = "cisco_input.jinja"
TEMPLATE_CISCO_RESULTS = "cisco_results.jinja"

CONTENT_TYPE = 'text/xml'
MAX_ITEM_PER_PAGE = 16


class CiscoViewPlugin(BaseViewPlugin):

    cisco_menu = '/directories/menu/<profile>/<user_uuid>/cisco'
    cisco_input = '/directories/input/<profile>/<user_uuid>/cisco'
    cisco_lookup = '/directories/lookup/<profile>/<user_uuid>/cisco'

    def load(self, dependencies):
        api = dependencies['api']
        auth_client = dependencies['auth_client']
        phone_lookup_service = new_phone_lookup_service_from_args(dependencies)

        api.add_resource(
            PhoneMenu,
            self.cisco_menu,
            endpoint='CiscoPhoneMenu',
            resource_class_args=(TEMPLATE_CISCO_MENU, CONTENT_TYPE),
        )
        api.add_resource(
            PhoneInput,
            self.cisco_input,
            endpoint='CiscoPhoneInput',
            resource_class_args=(TEMPLATE_CISCO_INPUT, CONTENT_TYPE),
        )
        api.add_resource(
            PhoneLookup,
            self.cisco_lookup,
            endpoint='CiscoPhoneLookup',
            resource_class_args=(
                TEMPLATE_CISCO_RESULTS,
                CONTENT_TYPE,
                phone_lookup_service,
                auth_client,
                MAX_ITEM_PER_PAGE,
            ),
        )
