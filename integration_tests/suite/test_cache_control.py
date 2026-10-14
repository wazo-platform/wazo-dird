# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import contextmanager

from hamcrest import assert_that, equal_to, none

from .helpers.base import BaseDirdIntegrationTest
from .helpers.constants import VALID_TOKEN_MAIN_TENANT
from .helpers.fixtures import http as fixtures


class TestCacheControl(BaseDirdIntegrationTest):
    """The asset configures `rest_api.cache_control.profile_sources: 3600`."""

    asset = 'all_routes'

    @contextmanager
    def profile(self, body):
        profile = self.client.profiles.create(body)
        try:
            yield profile
        finally:
            self.client.profiles.delete(profile['uuid'])

    @fixtures.display()
    @fixtures.csv_source()
    def test_sources_of_a_profile_stay_fresh_for_the_configured_lifetime(
        self, source, display
    ):
        body = {
            'name': 'cache_control',
            'display': display,
            'services': {'lookup': {'sources': [source]}},
        }
        with self.profile(body) as profile:
            url = self.url('directories', profile['name'], 'sources')

            response = self.get(url, token=VALID_TOKEN_MAIN_TENANT)

            assert_that(response.status_code, equal_to(200))
            assert_that(
                response.headers.get('Cache-Control'),
                equal_to('private, max-age=3600'),
            )

    def test_an_unconfigured_resource_stays_uncacheable(self):
        url = self.url('displays')

        response = self.get(url, token=VALID_TOKEN_MAIN_TENANT)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.headers.get('Cache-Control'), none())

    def test_an_error_response_stays_uncacheable(self):
        url = self.url('directories', 'not-a-profile', 'sources')

        response = self.get(url, token=VALID_TOKEN_MAIN_TENANT)

        assert_that(response.status_code, equal_to(404))
        assert_that(response.headers.get('Cache-Control'), none())
