# Copyright 2016-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

import requests
import yaml
from openapi_spec_validator import openapi_v2_spec_validator, validate_spec

from .helpers.base import DirdAssetRunningTestCase

logger = logging.getLogger('openapi_spec_validator')
logger.setLevel(logging.INFO)


class TestDocumentation(DirdAssetRunningTestCase):
    asset = 'documentation'

    def test_documentation_errors(self):
        port = self.service_port(9489, 'dird')
        api_url = f'http://127.0.0.1:{port}/0.1/api/api.yml'
        api = requests.get(api_url)
        api.raise_for_status()
        validate_spec(yaml.safe_load(api.text), validator=openapi_v2_spec_validator)
