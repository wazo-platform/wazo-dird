# -*- coding: utf-8 -*-
#
# Copyright 2016-2017 The Wazo Authors  (see the AUTHORS file)
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

import logging
import yaml

from flask import make_response
from pkg_resources import resource_string, iter_entry_points
from xivo.chain_map import ChainMap

from xivo_dird.core.rest_api import api, ErrorCatchingResource

from xivo_dird import BaseViewPlugin


logger = logging.getLogger(__name__)


class ApiViewPlugin(BaseViewPlugin):

    def load(self, args):
        api.add_resource(SwaggerResource, '/api/api.yml')


class SwaggerResource(ErrorCatchingResource):

    api_package = "xivo_dird.views"
    api_filename = "api.yml"

    def get(self):
        specs = []
        for module in iter_entry_points(group=self.api_package):
            try:
                plugin_package = module.module_name.rsplit('.', 1)[0]
                spec = yaml.load(resource_string(plugin_package, self.api_filename))
                specs.append(spec)
            except IOError:
                logger.debug('API spec for module "%s" does not exist', module.module_name)
            except IndexError:
                logger.debug('Could not find API spec from module "%s"', module.module_name)
        api_spec = ChainMap(*specs)

        if not api_spec.get('info'):
            return {'error': "API spec does not exist"}, 404

        return make_response(yaml.dump(dict(api_spec)), 200, {'Content-Type': 'application/x-yaml'})

