# Copyright 2014-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import equal_to
from wazo_dird import make_result_class

from ..plugin import SamplePlugin


class TestSampleBackend(unittest.TestCase):

    def setUp(self):
        self.source = SamplePlugin()

    def test_load_empty_config_does_not_raise(self):
        self.source.load({})

    def test_search(self):
        SourceResult = make_result_class('sample_directory', 'id')
        only_result = SourceResult({
            'id': 1,
            'firstname': 'John',
            'lastname': 'Doe',
            'number': '555',
            'description': 'It works but this wazo-dird installation is still using the default configuration',
        })

        self.source.load({})
        results = self.source.search('anything')

        assert_that(results, contains(only_result))

    def test_first_match(self):
        SourceResult = make_result_class('sample_directory', 'id')
        only_result = SourceResult({
            'id': 1,
            'firstname': 'John',
            'lastname': 'Doe',
            'number': '555',
            'description': 'It works but this wazo-dird installation is still using the default configuration',
        })

        self.source.load({})
        result = self.source.first_match('555')

        assert_that(result, equal_to(only_result))
