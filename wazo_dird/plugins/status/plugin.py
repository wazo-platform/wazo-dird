# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import BaseViewPlugin

from .http import StatusResource


class StatusViewPlugin(BaseViewPlugin):

    url = '/status'

    def load(self, dependencies):
        api = dependencies['api']

        status_aggregator = dependencies['status_aggregator']

        api.add_resource(StatusResource, '/status', resource_class_args=[status_aggregator])
