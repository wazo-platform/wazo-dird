# Copyright 2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import requests

from .helpers.base import BaseDirdIntegrationTest
from .helpers.constants import VALID_TOKEN_MAIN_TENANT


class TestEmptyBodyReturns400(BaseDirdIntegrationTest):
    asset = 'all_routes'

    def test_that_empty_body_returns_400(self):
        headers = {
            'X-Auth-Token': VALID_TOKEN_MAIN_TENANT,
        }

        response = requests.post(self.url('displays'), headers=headers, data='')
        assert response.status_code == 400

        response = requests.post(self.url('displays'), headers=headers, data=None)
        assert response.status_code == 400

        response = requests.post(self.url('profiles'), headers=headers, data='')
        assert response.status_code == 400

        response = requests.post(self.url('profiles'), headers=headers, data=None)
        assert response.status_code == 400

        response = requests.patch(self.url('config'), headers=headers, data='')
        assert response.status_code == 400

        response = requests.patch(self.url('config'), headers=headers, data=None)
        assert response.status_code == 400
