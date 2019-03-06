# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from wazo_dird import BaseViewPlugin
from wazo_dird.plugins.phone_helpers import new_phone_lookup_service_from_args
from wazo_dird.plugins.phone.http import PhoneLookup

TEMPLATE_YEALINK_RESULTS = "yealink_results.jinja"

CONTENT_TYPE = 'text/xml'


class YealinkViewPlugin(BaseViewPlugin):

    yealink_lookup = '/directories/lookup/<profile>/<xivo_user_uuid>/yealink'

    def load(self, dependencies):
        api = dependencies['api']
        auth_client = dependencies['auth_client']
        phone_lookup_service = new_phone_lookup_service_from_args(dependencies)

        api.add_resource(
            PhoneLookup,
            self.yealink_lookup,
            endpoint='YealinkPhoneLookup',
            resource_class_args=(
                TEMPLATE_YEALINK_RESULTS,
                CONTENT_TYPE,
                phone_lookup_service,
                auth_client,
            ),
        )
