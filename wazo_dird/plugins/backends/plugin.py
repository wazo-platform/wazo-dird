# Copyright 2018-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import BaseViewPlugin

from . import http, service


class BackendsViewPlugin(BaseViewPlugin):
    def load(self, dependencies):
        api = dependencies['api']
        backend_service = service.BackendService(dependencies['config'])

        api.add_resource(
            http.Backends, '/backends', resource_class_args=(backend_service,)
        )
