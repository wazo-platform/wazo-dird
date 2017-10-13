# -*- coding: utf-8 -*-
# Copyright 2016-2017 The Wazo Authors  (see the AUTHORS file)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

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
