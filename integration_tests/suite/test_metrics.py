# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import requests
from hamcrest import assert_that, contains_string, equal_to

from .helpers.base import BaseDirdIntegrationTest


class TestMetrics(BaseDirdIntegrationTest):
    asset = 'all_routes'

    def test_metrics_without_token(self):
        self.dird.status.get()

        response = requests.get(f'http://{self.host}:{self.port}/0.1/metrics')

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.text,
            contains_string('flask_http_request_total{method="GET",status="200"}'),
        )
        assert_that(
            response.text,
            contains_string(
                'flask_http_request_duration_seconds_count'
                '{endpoint="statusresource",method="GET",status="200"}'
            ),
        )
