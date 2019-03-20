# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import BaseViewPlugin

from . import http


class DisplaysViewPlugin(BaseViewPlugin):

    def load(self, dependencies):
        api = dependencies['api']

        api.add_resource(
            http.Displays,
            '/displays',
        )

        api.add_resource(
            http.Display,
            '/displays/<display_uuid>',
        )
