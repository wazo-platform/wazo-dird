# Copyright 2016-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import yaml

from flask import make_response
from pkg_resources import resource_string, iter_entry_points
from xivo.chain_map import ChainMap

from wazo_dird.rest_api import api, ErrorCatchingResource

from wazo_dird import BaseViewPlugin


logger = logging.getLogger(__name__)


class ApiViewPlugin(BaseViewPlugin):

    def load(self, args):
        api.add_resource(ApiResource, '/api/api.yml')


class ApiResource(ErrorCatchingResource):

    api_entry_point = "wazo_dird.views"
    api_filename = "api.yml"

    def get(self):
        specs = []
        for module in iter_entry_points(group=self.api_entry_point):
            try:
                plugin_package = module.module_name.rsplit('.', 1)[0]
                spec = yaml.load(resource_string(plugin_package, self.api_filename))
                specs.append(spec)
            except ImportError:
                logger.debug('failed to import %s', plugin_package)
            except IOError:
                logger.debug('API spec for module "%s" does not exist', module.module_name)
            except IndexError:
                logger.debug('Could not find API spec from module "%s"', module.module_name)
        api_spec = ChainMap(*specs)

        if not api_spec.get('info'):
            return {'error': "API spec does not exist"}, 404

        return make_response(yaml.dump(dict(api_spec)), 200, {'Content-Type': 'application/x-yaml'})
