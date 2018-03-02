# -*- coding: utf-8 -*-
# Copyright 2016-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import requests
import pprint

from hamcrest import assert_that, empty

from .base_dird_integration_test import BaseDirdIntegrationTest


class TestDocumentation(BaseDirdIntegrationTest):

    asset = 'documentation'

    def test_documentation_errors(self):
        api_url = 'https://dird:9489/0.1/api/api.yml'
        self.validate_api(api_url)

    def validate_api(self, url):
        validator_port = self.service_port(8080, 'swagger-validator')
        validator_url = u'http://localhost:{port}/debug'.format(port=validator_port)
        response = requests.get(validator_url, params={'url': url})
        assert_that(response.json(), empty(), pprint.pformat(response.json()))
