# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Avencall
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
import os
import random
import string
import tempfile

from hamcrest import assert_that
from hamcrest import contains_inanyorder
from hamcrest import contains
from xivo_dird.plugins.csv_plugin import CSVPlugin

coma_separated_content = '''\
clientno,firstname,lastname,number,age
1,Alice,AAA,5555555555,20
2,Bob,BBB,5555551234,21
3,Charles,CCC,5555556666,22
'''


class TestCsvDirectorySource(unittest.TestCase):

    @classmethod
    def setupClass(cls):
        cls.fd, cls.fname = tempfile.mkstemp()
        cls.tmp_file = os.fdopen(cls.fd)

        with open(cls.fname, 'w') as f:
            f.write(coma_separated_content)

    @classmethod
    def teardownClass(cls):
        os.remove(cls.fname)

    def setUp(self):
        self.alice = {'clientno': '1',
                      'firstname': 'Alice',
                      'lastname': 'AAA',
                      'number': '5555555555',
                      'age': '20'}
        self.bob = {'clientno': '2',
                    'firstname': 'Bob',
                    'lastname': 'BBB',
                    'number': '5555551234',
                    'age': '21'}
        self.charles = {'clientno': '3',
                        'firstname': 'Charles',
                        'lastname': 'CCC',
                        'number': '5555556666',
                        'age': '22'}

    def test_load_empty_config(self):
        source = CSVPlugin({})

        result = source.search('foo')

        assert_that(result, contains())

    def test_load_invalid_file_does_not_crash(self):
        config = {
            'file': self._generate_random_non_existent_filename()
        }

        source = CSVPlugin(config)

        result = source.search('foo')

        assert_that(result, contains())

    def test_load_file(self):
        config = {
            'file': self.fname,
        }

        s = CSVPlugin(config)

        assert_that(s._content, contains_inanyorder(self.alice, self.bob, self.charles))

    def test_search(self):
        config = {
            'file': self.fname,
            'searched_columns': ['firstname', 'lastname'],
        }

        s = CSVPlugin(config)

        results = s.search('ice')

        assert_that(results, contains(self.alice))

    def test_search_not_search_column(self):
        config = {
            'file': self.fname,
            'searched_columns': ['lastname'],
        }

        s = CSVPlugin(config)

        results = s.search('ice')

        assert_that(results, contains())

    def test_search_no_search_column(self):
        config = {
            'file': self.fname,
        }

        s = CSVPlugin(config)

        results = s.search('ice')

        assert_that(results, contains())

    def _generate_random_non_existent_filename(self):
        while True:
            name = ''.join(random.choice(string.lowercase) for _ in xrange(10))
            fullname = os.path.join('/tmp', name)
            if os.path.exists(fullname):
                continue
            return fullname
