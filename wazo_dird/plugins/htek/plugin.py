# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import BaseViewPlugin
from wazo_dird.plugins.phone_helpers import new_phone_lookup_service_from_args
from wazo_dird.plugins.phone.http import PhoneLookup

TEMPLATE_HTEK_RESULTS = "htek_results.jinja"

CONTENT_TYPE = 'text/xml'


class HtekViewPlugin(BaseViewPlugin):

    htek_lookup = '/directories/lookup/<profile>/<user_uuid>/htek'

    def load(self, dependencies):
        api = dependencies['api']
        auth_client = dependencies['auth_client']
        phone_lookup_service = new_phone_lookup_service_from_args(dependencies)

        api.add_resource(
            PhoneLookup,
            self.htek_lookup,
            endpoint='HtekPhoneLookup',
            resource_class_args=(
                TEMPLATE_HTEK_RESULTS,
                CONTENT_TYPE,
                phone_lookup_service,
                auth_client,
            ),
        )
