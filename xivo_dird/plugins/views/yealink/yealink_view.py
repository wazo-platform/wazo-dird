# -*- coding: utf-8 -*-
# Copyright 2015-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo_dird import BaseViewPlugin
from xivo_dird.rest_api import api
from xivo_dird.plugins.phone_helpers import new_phone_lookup_service_from_args
from xivo_dird.plugins.views.phone.phone_view import PhoneLookup

TEMPLATE_YEALINK_RESULTS = "yealink_results.jinja"

CONTENT_TYPE = 'text/xml'


class YealinkViewPlugin(BaseViewPlugin):

    yealink_lookup = '/directories/lookup/<profile>/<xivo_user_uuid>/yealink'

    def load(self, args=None):
        phone_lookup_service = new_phone_lookup_service_from_args(args)
        api.add_resource(PhoneLookup, self.yealink_lookup, endpoint='YealinkPhoneLookup',
                         resource_class_args=(TEMPLATE_YEALINK_RESULTS, CONTENT_TYPE,
                                              phone_lookup_service))
