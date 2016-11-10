# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Proformatique, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

from flask import make_response
from pkg_resources import resource_string

from xivo_dird.core.rest_api import api, ErrorCatchingResource

from xivo_dird import BaseViewPlugin


class ApiViewPlugin(BaseViewPlugin):

    def load(self, args):
        api.add_resource(SwaggerResource, '/api/api.yml')


class SwaggerResource(ErrorCatchingResource):

    api_package = "xivo_dird.plugins.views.api"
    api_filename = "api.yml"

    @classmethod
    def add_resource(cls, api):
        api.add_resource(cls, cls.api_path)

    def get(self):
        try:
            api_spec = resource_string(self.api_package, self.api_filename)
        except IOError:
            return {'error': "API spec does not exist"}, 404
        return make_response(api_spec, 200, {'Content-Type': 'application/x-yaml'})
