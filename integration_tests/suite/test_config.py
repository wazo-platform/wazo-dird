# Copyright 2022-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, calling, equal_to, has_entry, has_key, has_properties
from wazo_dird_client.exceptions import DirdError
from wazo_test_helpers import until
from wazo_test_helpers.hamcrest.raises import raises

from .helpers.base import BaseDirdIntegrationTest
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

        assert_that(
            calling(dird.config.patch).with_args({}),
            raises(DirdError).matching(has_properties(status_code=401)),
        )

    def test_restrict_when_service_token_not_initialized(self):
        def _returns_503():
            assert_that(
                calling(self.dird.config.get).with_args(MAIN_TENANT),
                raises(DirdError).matching(
                    has_properties(
                        status_code=503,
                        error_id='matser-tenant-not-initiated',
                    )
                ),
            )

        config = {'auth': {'username': 'invalid-service'}}
        with self.dird_with_config(config):
            until.assert_(_returns_503, timeout=10)

    def test_update_config(self) -> None:
        debug_true_config = [
            {
                'op': 'replace',
                'path': '/debug',
                'value': True,
            }
        ]

        debug_false_config = [
            {
                'op': 'replace',
                'path': '/debug',
                'value': False,
            }
        ]

        dird = self.make_dird(VALID_TOKEN_MAIN_TENANT)

        debug_true_patched_config = dird.config.patch(debug_true_config)
        debug_true_updated_config = dird.config.get()
        assert_that(debug_true_patched_config, equal_to(debug_true_updated_config))
        assert_that(debug_true_updated_config, has_entry('debug', True))

        debug_false_patched_config = dird.config.patch(debug_false_config)
        debug_false_updated_config = dird.config.get()
        assert_that(debug_false_patched_config, equal_to(debug_false_updated_config))
        assert_that(debug_false_updated_config, has_entry('debug', False))

    def test_that_empty_body_for_patch_config_returns_400(self):
        self.assert_empty_body_returns_400([('patch', 'config')])
