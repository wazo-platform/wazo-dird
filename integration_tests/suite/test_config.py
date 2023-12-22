# Copyright 2022-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, calling, has_key, has_properties
from wazo_dird_client.exceptions import DirdError
from wazo_test_helpers import until
from wazo_test_helpers.hamcrest.raises import raises

from .helpers.base import START_TIMEOUT, BaseDirdIntegrationTest
from .helpers.constants import (
    MAIN_TENANT,
    SUB_TENANT,
    VALID_TOKEN_MAIN_TENANT,
    VALID_TOKEN_SUB_TENANT,
)
from .helpers.wait_strategy import EverythingOkWaitStrategy


class TestConfig(BaseDirdIntegrationTest):
    asset = 'all_routes'
    wait_strategy = EverythingOkWaitStrategy()

    def test_config_with_master_tenant(self):
        dird = self.make_dird(VALID_TOKEN_MAIN_TENANT)
        result = dird.config.get(MAIN_TENANT)

        assert_that(result, has_key('rest_api'))

    def test_restrict_only_master_tenant(self):
        dird = self.make_dird(VALID_TOKEN_SUB_TENANT)

        assert_that(
            calling(dird.config.get).with_args(SUB_TENANT),
            raises(DirdError).matching(has_properties(status_code=401)),
        )

    def test_restrict_when_auth_service_is_down(self):
        self.stop_service('dird')
        self.stop_service('auth')
        self.start_service('dird')
        dird = self.make_dird(VALID_TOKEN_MAIN_TENANT)

        def _returns_503():
            assert_that(
                calling(dird.config.get).with_args(MAIN_TENANT),
                raises(DirdError).matching(
                    has_properties(
                        status_code=503,
                        error_id='matser-tenant-not-initiated',
                    )
                ),
            )

        until.assert_(_returns_503, tries=10)

        self.start_service('auth')
        auth = self.make_mock_auth()
        until.true(auth.is_up, timeout=START_TIMEOUT)
        self.configure_wazo_auth()

        def _not_return_503():
            try:
                response = dird.config.get(MAIN_TENANT)
                assert_that(response, has_key('debug'))
            except Exception as e:
                raise AssertionError(e)

        until.assert_(_not_return_503, tries=10)
