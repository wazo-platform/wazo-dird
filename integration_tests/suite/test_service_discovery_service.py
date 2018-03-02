# -*- coding: utf-8 -*-
# Copyright (C) 2016 Proformatique, Inc.
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import assert_that, contains, has_entry

from xivo_test_helpers import until

from .base_dird_integration_test import BaseDirdIntegrationTest


class TestDiscoveredXiVOUser(BaseDirdIntegrationTest):

    asset = 'xivo_users_disco'

    def test_that_the_source_is_loaded(self):
        def test():
            result = self.lookup('dyl', 'default')
            assert_that(result['results'],
                        contains(has_entry('column_values',
                                           contains('Bob', 'Dylan', '1000', ''))))

        until.assert_(test, tries=3)
