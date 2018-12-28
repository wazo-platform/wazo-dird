# Copyright 2015-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from wazo_dird import BaseViewPlugin
from wazo_dird.plugins.phone_helpers import new_phone_lookup_service_from_args
from wazo_dird.plugins.phone.http import PhoneInput, PhoneLookup

TEMPLATE_AASTRA_INPUT = "aastra_input.jinja"
TEMPLATE_AASTRA_RESULTS = "aastra_results.jinja"

CONTENT_TYPE = 'text/xml'
MAX_ITEM_PER_PAGE = 16


class AastraViewPlugin(BaseViewPlugin):

    aastra_input = '/directories/input/<profile>/<xivo_user_uuid>/aastra'
    aastra_lookup = '/directories/lookup/<profile>/<xivo_user_uuid>/aastra'

    def load(self, dependencies):
        api = dependencies['api']
        phone_lookup_service = new_phone_lookup_service_from_args(dependencies)
        api.add_resource(PhoneInput, self.aastra_input, endpoint='AastraPhoneInput',
                         resource_class_args=(TEMPLATE_AASTRA_INPUT, CONTENT_TYPE))
        api.add_resource(PhoneLookup, self.aastra_lookup, endpoint='AastraPhoneLookup',
                         resource_class_args=(TEMPLATE_AASTRA_RESULTS, CONTENT_TYPE,
                                              phone_lookup_service, MAX_ITEM_PER_PAGE))
