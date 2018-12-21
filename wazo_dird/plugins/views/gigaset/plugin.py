# Copyright 2015-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from wazo_dird import BaseViewPlugin
from wazo_dird.rest_api import api
from wazo_dird.plugins.phone_helpers import new_phone_lookup_service_from_args
from wazo_dird.plugins.views.phone.http import PhoneLookup

TEMPLATE_GIGASET_RESULTS = "gigaset_results.jinja"

CONTENT_TYPE = 'text/xml'


class GigasetViewPlugin(BaseViewPlugin):

    gigaset_lookup = '/directories/lookup/<profile>/<xivo_user_uuid>/gigaset'

    def load(self, args=None):
        phone_lookup_service = new_phone_lookup_service_from_args(args)
        api.add_resource(PhoneLookup, self.gigaset_lookup, endpoint='GigasetPhoneLookup',
                         resource_class_args=(TEMPLATE_GIGASET_RESULTS, CONTENT_TYPE,
                                              phone_lookup_service))
