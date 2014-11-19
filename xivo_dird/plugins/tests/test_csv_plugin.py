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
from hamcrest import equal_to
from xivo_dird.plugins.csv_plugin import CSVPlugin
from xivo_dird import make_result_class

comma_separated_content = '''\
clientno,firstname,lastname,number,age
1,Alice,AAA,5555555555,20
2,Bob,BBB,5555551234,21
3,Charles,CCC,5555556666,22
'''

pipe_separated_content = comma_separated_content.replace(',', '|')

SourceResult = make_result_class('my_directory', 'client_no')

alice = {'clientno': '1',
         'firstname': 'Alice',
         'lastname': 'AAA',
         'number': '5555555555',
         'age': '20'}


class BaseCSVTestDirectory(unittest.TestCase):

    @classmethod
    def setupClass(cls):
        cls.fd, cls.fname = tempfile.mkstemp()
        cls.tmp_file = os.fdopen(cls.fd)

        with open(cls.fname, 'w') as f:
            f.write(cls.content)

    @classmethod
    def teardownClass(cls):
        os.remove(cls.fname)


class TestCSVDirectorySourceSeparator(BaseCSVTestDirectory):

    content = pipe_separated_content

    def test_search_with_diferent_separator(self):
        self.source = CSVPlugin()
        config = {
            'file': self.fname,
            'unique_columns': ['clientno'],
            'searched_columns': ['firstname'],
            'name': 'my_directory',
            'separator': '|',
        }

        self.source.load({'config': config})

        results = self.source.search('ice')

        assert_that(results, contains(SourceResult(alice)))


class TestCsvDirectorySource(BaseCSVTestDirectory):

    content = comma_separated_content

    def setUp(self):
        self.name = 'my_directory'
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
        self.source = CSVPlugin()
        self.alice_result = SourceResult(alice)
        self.charles_result = SourceResult(self.charles)

    def test_load_empty_config(self):
        self.source.load({})

        result = self.source.search('foo')

        assert_that(result, contains())

    def test_load_invalid_file_does_not_crash(self):
        config = {
            'file': self._generate_random_non_existent_filename(),
            'name': self.name,
        }

        self.source.load({'config': config})

        result = self.source.search('foo')

        assert_that(result, contains())

    def test_load_file(self):
        config = {
            'file': self.fname,
            'name': self.name,
        }

        self.source.load({'config': config})

        assert_that(self.source._content, contains_inanyorder(alice, self.bob, self.charles))

    def test_search(self):
        config = {
            'file': self.fname,
            'searched_columns': ['firstname', 'lastname'],
            'name': self.name,
            'unique_columns': ['clientno'],
        }

        self.source.load({'config': config})

        results = self.source.search('ice')

        assert_that(results, contains(self.alice_result))

    def test_search_not_search_column(self):
        config = {
            'file': self.fname,
            'searched_columns': ['lastname'],
            'name': 'my_dir',
        }

        self.source.load({'config': config})

        results = self.source.search('ice')

        assert_that(results, contains())

    def test_search_no_search_column(self):
        config = {
            'file': self.fname,
            'name': 'my_dir',
        }

        self.source.load({'config': config})

        results = self.source.search('ice')

        assert_that(results, contains())

    def test_search_with_unique_defined(self):
        config = {
            'file': self.fname,
            'unique_columns': ['clientno'],
            'searched_columns': ['firstname'],
            'name': self.name,
        }

        self.source.load({'config': config})

        results = self.source.search('ice')

        assert_that(results, contains(self.alice_result))

    def test_list_no_unique(self):
        config = {
            'file': self.fname,
            'name': 'my_dir',
        }

        self.source.load({'config': config})

        results = self.source.list([('1',), ('3',)])

        assert_that(results, contains())

    def test_list_empty_unique(self):
        config = {
            'file': self.fname,
            'unique_columns': [],
            'name': self.name,
        }

        self.source.load({'config': config})

        results = self.source.list([('1',), ('3',)])

        assert_that(results, contains())

    def test_list_one_field(self):
        config = {
            'file': self.fname,
            'unique_columns': ['clientno'],
            'name': self.name,
        }

        self.source.load({'config': config})

        results = self.source.list([('1',), ('3',)])

        assert_that(results, contains(self.alice_result, self.charles_result))

    def test_list_many_field(self):
        config = {
            'file': self.fname,
            'unique_columns': ['firstname', 'lastname'],
            'name': self.name,
        }

        self.source.load({'config': config})

        results = self.source.list([('Alice', 'AAA'), ('Charles', 'CCC')])

        assert_that(results, contains(self.alice_result, self.charles_result))

    def test_row_to_dict(self):
        keys = ['one', 'two', 'three']
        values = [1, 2, 3]

        result = CSVPlugin._row_to_dict(keys, values)

        assert_that(result, equal_to({'one': 1, 'two': 2, 'three': 3}))

    def test_is_in_unique_ids(self):
        config = {
            'file': self.fname,
            'unique_columns': ['firstname', 'lastname'],
            'name': 'my_dir',
        }

        self.source.load({'config': config})

        result = self.source._is_in_unique_ids([('Alice', 'AAA')], {'firstname': 'Alice', 'lastname': 'AAA'})

        assert_that(result, equal_to(True))

        result = self.source._is_in_unique_ids([('Alice', 'AAA')], {'firstname': 'Bob', 'lastname': 'BBB'})

        assert_that(result, equal_to(False))

    def test_low_case_match_entry(self):
        config = {
            'file': self.fname,
            'unique_columns': ['firstname', 'lastname'],
            'name': 'my_dir',
        }

        term = 'ice'
        columns = ['firstname', 'lastname']

        self.source.load({'config': config})

        result = self.source._low_case_match_entry(term, columns, alice)

        assert_that(result, equal_to(True))

    def test_low_case_match_entry_broken_config(self):
        config = {
            'file': self.fname,
            'unique_columns': ['firstname', 'lastname'],
            'name': 'my_dir',
        }

        term = 'ice'
        columns = [None, 'firstname', 'lastname']

        self.source.load({'config': config})

        result = self.source._low_case_match_entry(term, columns, alice)

        assert_that(result, equal_to(True))

    def _generate_random_non_existent_filename(self):
        while True:
            name = ''.join(random.choice(string.lowercase) for _ in xrange(10))
            fullname = os.path.join('/tmp', name)
            if os.path.exists(fullname):
                continue
            return fullname
