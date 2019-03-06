# Copyright 2016-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import skip

from hamcrest import (
    assert_that,
    contains,
    has_entry,
)

from xivo_test_helpers import until

from .base_dird_integration_test import BaseDirdIntegrationTest


@skip('fix the implementation')
class TestDiscoveredWazoUser(BaseDirdIntegrationTest):

    asset = 'wazo_users_disco'
    displays = [
        {
            'name': 'default_display',
            'columns': [
                {
                    'title': 'Firstname',
                    'field': 'firstname',
                },
                {
                    'title': 'Lastname',
                    'field': 'lastname',
                },
                {
                    'title': 'Number',
                    'default': '',
                    'field': 'number',
                },
                {
                    'title': 'Mobile',
                    'default': '',
                    'field': 'mobile_phone_number',
                },
            ],
        },
    ]

    def test_that_the_source_is_loaded(self):

        def test():
            result = self.lookup('dyl', 'default')
            assert_that(result['results'],
                        contains(has_entry('column_values',
                                           contains('Bob', 'Dylan', '1000', ''))))

        until.assert_(test, tries=3)
