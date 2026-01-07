# Copyright 2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import requests

from .helpers.base import BaseDirdIntegrationTest
from .helpers.constants import VALID_TOKEN_MAIN_TENANT


class TestEmptyBodyReturns400(BaseDirdIntegrationTest):
    asset = 'all_routes'

    def _make_http_call(self, verb: str, url: str, body: str | None):
        headers = {
            'X-Auth-Token': VALID_TOKEN_MAIN_TENANT,
        }

        match verb:
            case 'post':
                call = requests.post
            case 'patch':
                call = requests.patch  # type: ignore

        return call(
            url,
            headers=headers,
            data=body,
            verify=False,
        )

    def test_that_empty_body_returns_400(self):
        urls = [
            ('post', self.url('displays')),
            ('post', self.url('profiles')),
            ('patch', self.url('config')),
        ]

        for url in urls:
            response = self._make_http_call(url[0], url[1], '')
            assert response.status_code == 400, f'Error for url: {url}'

            response = self._make_http_call(url[0], url[1], None)
            assert response.status_code == 400, f'Error for url: {url}'
