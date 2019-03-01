# Copyright 2016-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import assert_that, has_entries

from .base_dird_integration_test import BaseDirdIntegrationTest, VALID_TOKEN_MAIN_TENANT


class TestConfigView(BaseDirdIntegrationTest):

    asset = 'config-view'

    def test_get_config(self):
        result = self.get_config(token=VALID_TOKEN_MAIN_TENANT)

        assert_that(result, has_entries({'foo': {'bar': 'main',
                                                 'baz': 'conf.d',
                                                 'other': 'overwritten'}}))
