# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import (
    assert_that,
    equal_to,
)
from .base_dird_integration_test import (
    BaseDirdIntegrationTest,
    VALID_TOKEN,
)


class TestDBRestart(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def tearDown(self):
        self.purge_personal()

    def test_query_after_db_restart(self):
        self.post_personal({'firstname': 'Alice'}, token=VALID_TOKEN)

        self.restart_postgres()

        bob = self.post_personal({'firstname': 'Bob'}, token=VALID_TOKEN)
        assert_that(bob['firstname'], equal_to('Bob'))
