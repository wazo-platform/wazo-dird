# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from wazo_dird import BaseViewPlugin
from wazo_dird.rest_api import api

from . import http
from . import service


class BackendsViewPlugin(BaseViewPlugin):

    def load(self, args):
        backend_service = service.BackendService(args['config'])
        api.add_resource(
            http.Backends,
            '/backends',
            resource_class_args=(backend_service,),
        )
