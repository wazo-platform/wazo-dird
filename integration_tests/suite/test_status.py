# Copyright 2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    has_entries,
)
from wazo_test_helpers import until

from .helpers.base import (
    BaseDirdIntegrationTest,
    MASTER_TENANT,
    MASTER_TOKEN,
)
from .helpers.wait_strategy import EverythingOkWaitStrategy


class TestStatusAllOK(BaseDirdIntegrationTest):
    asset = 'all_routes'
    wait_strategy = EverythingOkWaitStrategy()

    def test_when_status_then_status_ok(self):
        dird = self.make_dird(MASTER_TOKEN)

        def status_ok():
            result = dird.status.get(MASTER_TENANT)
            assert_that(
                result,
                has_entries(
                    {
                        'rest_api': has_entries({'status': 'ok'}),
                        'master_tenant': has_entries({'status': 'ok'}),
                    },
                ),
            )

        until.assert_(status_ok, timeout=5)
