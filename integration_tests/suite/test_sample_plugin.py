# -*- coding: utf-8 -*-
# Copyright (C) 2014 Avencall
# SPDX-License-Identifier: GPL-3.0+

from .base_dird_integration_test import BaseDirdIntegrationTest
from hamcrest import assert_that
from hamcrest import contains


class TestSamplePlugin(BaseDirdIntegrationTest):

    asset = 'sample_backend'

    def test_that_john_doe_is_returned(self):
        result = self.lookup('lol', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains('John', 'Doe', 'It works but this xivo-dird installation is still using the default configuration'))
