# Copyright 2016-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import BaseViewPlugin

from . import http


class ApiViewPlugin(BaseViewPlugin):

    def load(self, dependencies):
        api = dependencies['api']
        api_1 = dependencies['api_1']

        api.add_resource(http.ApiResource, '/api/api.yml')
        api_1.add_resource(http.ApiResourceV1, '/api/api.yml')
