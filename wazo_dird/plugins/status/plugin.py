# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.status import Status, StatusDict

from wazo_dird import BaseViewPlugin
from wazo_dird.plugin_manager import ViewDependencies

from .http import StatusResource


class StatusViewPlugin(BaseViewPlugin):
    url = '/status'

    def load(self, dependencies: ViewDependencies) -> None:
        api = dependencies['api']

        status_aggregator = dependencies['status_aggregator']

        status_aggregator.add_provider(provide_status)

        api.add_resource(
            StatusResource, '/status', resource_class_args=[status_aggregator]
        )


def provide_status(status: StatusDict) -> None:
    status['rest_api']['status'] = Status.ok
