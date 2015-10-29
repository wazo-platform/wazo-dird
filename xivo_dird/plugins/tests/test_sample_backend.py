# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import unittest

from ..sample_backend import SamplePlugin
from hamcrest import assert_that
from hamcrest import contains
from hamcrest import equal_to
from xivo_dird import make_result_class


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
            'description': 'It works but this xivo-dird installation is still using the default configuration',
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
            'description': 'It works but this xivo-dird installation is still using the default configuration',
        })

        self.source.load({})
        result = self.source.first_match('555')

        assert_that(result, equal_to(only_result))
