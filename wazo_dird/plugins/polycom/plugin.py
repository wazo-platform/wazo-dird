# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from wazo_dird import BaseViewPlugin
from wazo_dird.plugins.phone_helpers import new_phone_lookup_service_from_args
from wazo_dird.plugins.phone.http import PhoneInput, PhoneLookup

TEMPLATE_POLYCOM_INPUT = "polycom_input.jinja"
TEMPLATE_POLYCOM_RESULTS = "polycom_results.jinja"

CONTENT_TYPE = 'text/html; charset=UTF-8'
MAX_ITEM_PER_PAGE = 16


class PolycomViewPlugin(BaseViewPlugin):

    polycom_input = '/directories/input/<profile>/<xivo_user_uuid>/polycom'
    polycom_lookup = '/directories/lookup/<profile>/<xivo_user_uuid>/polycom'

    def load(self, dependencies):
        api = dependencies['api']
        auth_client = dependencies['auth_client']
        phone_lookup_service = new_phone_lookup_service_from_args(dependencies)

        api.add_resource(
            PhoneInput,
            self.polycom_input,
            endpoint='PolycomPhoneInput',
            resource_class_args=(TEMPLATE_POLYCOM_INPUT, CONTENT_TYPE))
        api.add_resource(
            PhoneLookup,
            self.polycom_lookup,
            endpoint='PolycomPhoneLookup',
            resource_class_args=(
                TEMPLATE_POLYCOM_RESULTS,
                CONTENT_TYPE,
                phone_lookup_service,
                auth_client,
                MAX_ITEM_PER_PAGE,
            ),
        )
