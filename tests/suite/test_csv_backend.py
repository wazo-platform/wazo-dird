# -*- coding: utf-8 -*-

# Copyright (C) 2014 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import subprocess
import unittest
import requests
import json
import os
import time

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import contains_inanyorder


class BaseDirdIntegrationTest(unittest.TestCase):

    @classmethod
    def launch_dird_with_asset(cls):
        asset_path = os.path.abspath(os.path.curdir) + '/tests/assets/%s' % cls.asset
        volumes = '%s:/etc/xivo/xivo-dird' % asset_path
        cmd = ['docker', 'run', '--name', __name__,
               '-v', volumes,
               '-d', '-p', '9489:9489', 'dird-test']
        subprocess.call(cmd)
        time.sleep(0.5)

    @classmethod
    def stop_dird_with_asset(cls):
        subprocess.call(['docker', 'kill', __name__])
        subprocess.call(['docker', 'rm', __name__])

    @classmethod
    def setupClass(cls):
        cls.launch_dird_with_asset()

    @classmethod
    def teardownClass(cls):
        cls.stop_dird_with_asset()

    def lookup(self, term, profile):
        url = 'http://localhost:9489/0.1/directories/lookup/{profile}?term={term}'
        result = requests.get(url.format(profile=profile, term=term))
        return json.loads(result.text)

    def headers(self, profile):
        url = 'http://localhost:9489/0.1/directories/lookup/{profile}/headers'
        result = requests.get(url.format(profile=profile))
        return json.loads(result.text)


class TestCSVBackend(BaseDirdIntegrationTest):

    asset = 'csv_with_multiple_displays'

    def test_that_searching_for_lice_return_Alice(self):
        result = self.lookup('lice', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains('Alice', 'AAA', '5555555555'))


class TestCoreSourceManagement(BaseDirdIntegrationTest):

    asset = 'multiple_sources'

    def test_multiple_source_from_the_same_backend(self):
        result = self.lookup('lice', 'default')

        # second_csv does not search in column firstname
        expected_results = [
            {'column_values': ['Alice', 'AAA', '5555555555'],
             'source': 'my_csv',
             'relations': {'user': None, 'endpoint': None, 'agent': None}},
            {'column_values': ['Alice', 'Alan', '1111'],
             'source': 'third_csv',
             'relations': {'user': None, 'endpoint': None, 'agent': None}},
        ]

        assert_that(result['results'],
                    contains_inanyorder(*expected_results))


class TestDisplay(BaseDirdIntegrationTest):

    asset = 'csv_with_multiple_displays'

    def test_that_the_display_is_really_applied_to_lookup(self):
        result = self.lookup('lice', 'default')

        assert_that(result['column_headers'], contains('Firstname', 'Lastname', 'Number'))
        assert_that(result['column_types'], contains(None, None, None))

    def test_display_with_a_type_only(self):
        result = self.lookup('lice', 'test')

        assert_that(result['column_headers'], contains('fn', 'ln', 'Empty', None, 'Default'))
        assert_that(result['column_types'], contains('firstname', None, None, 'status', None))
        assert_that(result['results'][0]['column_values'],
                    contains('Alice', 'AAA', None, None, 'Default'))

    def test_that_the_display_is_applied_to_headers(self):
        result = self.headers('default')

        assert_that(result['column_headers'], contains('Firstname', 'Lastname', 'Number'))
        assert_that(result['column_types'], contains(None, None, None))

    def test_display_on_headers_with_no_title(self):
        result = self.headers('test')

        assert_that(result['column_headers'],
                    contains('fn', 'ln', 'Empty', None, 'Default'))
        assert_that(result['column_types'],
                    contains('firstname', None, None, 'status', None))
