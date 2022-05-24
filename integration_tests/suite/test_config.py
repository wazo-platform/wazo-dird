# Copyright 2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    has_key,
    calling,
    has_properties,
)
from wazo_test_helpers import until
from wazo_dird_client.exceptions import DirdError
from wazo_test_helpers.hamcrest.raises import raises

from .helpers.wait_strategy import EverythingOkWaitStrategy
from .helpers.base import (
    BaseDirdIntegrationTest,
    MASTER_TENANT,
    START_TIMEOUT,
    MASTER_TOKEN,
    USER_1_TOKEN,
    USERS_TENANT,
)


class TestConfig(BaseDirdIntegrationTest):
    asset = 'all_routes'
    wait_strategy = EverythingOkWaitStrategy()

    def test_config_with_master_tenant(self):

        dird = self.make_dird(MASTER_TOKEN)
        result = dird.config.get(MASTER_TENANT)

        assert_that(result, has_key('rest_api'))

    def test_restrict_only_master_tenant(self):
        dird = self.make_dird(USER_1_TOKEN)

        assert_that(
            calling(dird.config.get).with_args(USERS_TENANT),
            raises(DirdError).matching(has_properties(status_code=401)),
        )

    def test_restrict_when_auth_service_is_down(self):
        self.stop_service('dird')
        self.stop_service('auth')
        self.start_service('dird')
        dird = self.make_dird(MASTER_TOKEN)

        def _returns_503():
            assert_that(
                calling(dird.config.get).with_args(MASTER_TENANT),
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
                response = dird.config.get(MASTER_TENANT)
                assert_that(response, has_key('debug'))
            except Exception as e:
                raise AssertionError(e)

        until.assert_(_not_return_503, tries=10)
