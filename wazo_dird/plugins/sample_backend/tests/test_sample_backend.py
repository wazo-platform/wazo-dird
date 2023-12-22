# Copyright 2014-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from hamcrest import assert_that, contains, equal_to

from wazo_dird import make_result_class

from ..plugin import SamplePlugin

MSG = (
    'It works but this wazo-dird installation is still using the default configuration'
)


class TestSampleBackend(unittest.TestCase):
    def setUp(self):
        self.source = SamplePlugin()

    def test_load_empty_config_does_not_raise(self):
        self.source.load({})

    def test_search(self):
        SourceResult = make_result_class('sample_backend', 'sample_directory', 'id')
        only_result = SourceResult(
            {
                'id': 1,
                'firstname': 'John',
                'lastname': 'Doe',
                'number': '555',
                'description': MSG,
            }
        )

        self.source.load({})
        results = self.source.search('anything')

        assert_that(results, contains(only_result))

    def test_first_match(self):
        SourceResult = make_result_class('sample_backend', 'sample_directory', 'id')
        only_result = SourceResult(
            {
                'id': 1,
                'firstname': 'John',
                'lastname': 'Doe',
                'number': '555',
                'description': MSG,
            }
        )

        self.source.load({})
        result = self.source.first_match('555')

        assert_that(result, equal_to(only_result))
