# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import BaseViewPlugin

from . import http


class DisplaysViewPlugin(BaseViewPlugin):
    def load(self, dependencies):
        api = dependencies['api']
        display_service = dependencies['services']['display']

        api.add_resource(
            http.Displays, '/displays', resource_class_args=(display_service,)
        )

        api.add_resource(
            http.Display,
            '/displays/<display_uuid>',
            resource_class_args=(display_service,),
        )
