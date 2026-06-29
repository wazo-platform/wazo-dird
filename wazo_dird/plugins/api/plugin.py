# Copyright 2016-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import BaseViewPlugin
from wazo_dird.plugin_manager import ViewDependencies

from . import http


class ApiViewPlugin(BaseViewPlugin):
    def load(self, dependencies: ViewDependencies) -> None:
        api = dependencies['api']
        api.add_resource(http.ApiResource, '/api/api.yml')
