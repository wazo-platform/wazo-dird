# Copyright 2018-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, equal_to

from .helpers.base import BaseDirdIntegrationTest
from .helpers.constants import VALID_TOKEN_MAIN_TENANT


class TestDBRestart(BaseDirdIntegrationTest):
    asset = 'personal_only'

    def tearDown(self):
        self.purge_personal()

    def test_query_after_db_restart(self):
        self.post_personal({'firstname': 'Alice'}, token=VALID_TOKEN_MAIN_TENANT)

        self.restart_postgres()

        bob = self.post_personal({'firstname': 'Bob'}, token=VALID_TOKEN_MAIN_TENANT)
        assert_that(bob['firstname'], equal_to('Bob'))
