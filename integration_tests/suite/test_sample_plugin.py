# -*- coding: utf-8 -*-
# Copyright 2014-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import (
    assert_that,
    contains,
)
from .base_dird_integration_test import BaseDirdIntegrationTest


class TestSamplePlugin(BaseDirdIntegrationTest):

    asset = 'sample_backend'

    def test_that_john_doe_is_returned(self):
        result = self.lookup('lol', 'default')

        assert_that(
            result['results'][0]['column_values'],
            contains(
                'John',
                'Doe',
                'It works but this wazo-dird installation is still using the default configuration',
            ),
        )
