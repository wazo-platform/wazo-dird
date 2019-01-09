# Copyright 2016-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from wazo_dird import BaseViewPlugin
from wazo_dird.rest_api import api

from . import http


class ApiViewPlugin(BaseViewPlugin):

    def load(self, args):
        api.add_resource(http.ApiResource, '/api/api.yml')
