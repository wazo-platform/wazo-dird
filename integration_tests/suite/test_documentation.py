# Copyright 2016-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

import requests
import yaml
from openapi_spec_validator import openapi_v2_spec_validator, validate_spec

from .helpers.base import DirdAssetRunningTestCase

logger = logging.getLogger('openapi_spec_validator')
logger.setLevel(logging.INFO)


class TestDocumentation(DirdAssetRunningTestCase):
    asset = 'phonebook_only'

    def test_documentation_errors(self):
        port = self.service_port(9489, 'dird')
        api_url = f'http://127.0.0.1:{port}/0.1/api/api.yml'
        api = requests.get(api_url)
        api.raise_for_status()
        validate_spec(yaml.safe_load(api.text), validator=openapi_v2_spec_validator)

    def test_the_contacts_list_route_is_described(self):
        port = self.service_port(9489, 'dird')
        api = yaml.safe_load(
            requests.get(f'http://127.0.0.1:{port}/0.1/api/api.yml').text
        )

        route = api['paths']['/directories/contacts']['get']
        assert 'dird.directories.contacts.read' in route['description']
        assert {p['name'] for p in route['parameters']} == {'limit', 'offset'}
