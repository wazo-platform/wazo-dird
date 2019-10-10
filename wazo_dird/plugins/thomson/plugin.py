# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import BaseViewPlugin
from wazo_dird.plugins.phone_helpers import new_phone_lookup_service_from_args
from wazo_dird.plugins.phone.http import PhoneLookup

TEMPLATE_THOMSON_RESULTS = "thomson_results.jinja"

CONTENT_TYPE = 'text/xml'
MAX_ITEM_PER_PAGE = 8


class ThomsonViewPlugin(BaseViewPlugin):

    thomson_lookup = '/directories/lookup/<profile>/<user_uuid>/thomson'

    def load(self, dependencies):
        api = dependencies['api']
        auth_client = dependencies['auth_client']
        phone_lookup_service = new_phone_lookup_service_from_args(dependencies)

        api.add_resource(
            PhoneLookup,
            self.thomson_lookup,
            endpoint='ThomsonPhoneLookup',
            resource_class_args=(
                TEMPLATE_THOMSON_RESULTS,
                CONTENT_TYPE,
                phone_lookup_service,
                auth_client,
                MAX_ITEM_PER_PAGE,
            ),
        )
