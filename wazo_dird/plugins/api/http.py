# Copyright 2016-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

import yaml
from flask import make_response
from xivo.chain_map import ChainMap
from xivo.http_helpers import reverse_proxy_fix_api_spec
from xivo.rest_api_helpers import load_all_api_specs

from wazo_dird.http import ErrorCatchingResource

logger = logging.getLogger(__name__)


class ApiResource(ErrorCatchingResource):
    api_entry_point = "wazo_dird.views"
    api_filename = "api.yml"

    def get(self):
        api_spec = ChainMap(
            *load_all_api_specs(self.api_entry_point, self.api_filename)
        )

        if not api_spec.get('info'):
            return {'error': "API spec does not exist"}, 404

        reverse_proxy_fix_api_spec(api_spec)
        return make_response(
            yaml.dump(dict(api_spec)), 200, {'Content-Type': 'application/x-yaml'}
        )
