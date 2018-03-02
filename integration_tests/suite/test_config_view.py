# -*- coding: utf-8 -*-
# Copyright (C) 2016 Proformatique, Inc.
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import assert_that, has_entries

from .base_dird_integration_test import BaseDirdIntegrationTest, VALID_TOKEN


class TestConfigView(BaseDirdIntegrationTest):

    asset = 'config-view'

    def test_get_config(self):
        result = self.get_config(token=VALID_TOKEN)

        assert_that(result, has_entries({'foo': {'bar': 'main',
                                                 'baz': 'conf.d',
                                                 'other': 'overwritten'}}))
