# -*- coding: utf-8 -*-

# Copyright (C) 2015 Avencall
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

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import equal_to
from hamcrest import has_entries
from unittest import TestCase

from ..consul import dict_from_consul
from ..consul import ls_from_consul
from ..consul import tree_from_consul
from ..consul import dict_to_consul


class TestDictFromConsul(TestCase):

    def test_dict_from_consul_empty(self):
        result = dict_from_consul('', [])

        assert_that(result, equal_to({}))

    def test_dict_from_consul_none(self):
        result = dict_from_consul('', None)

        assert_that(result, equal_to({}))

    def test_dict_from_consul_full(self):
        consul_dict = [
            {'Key': '/my/prefix/key1',
             'Value': 'value1'},
            {'Key': '/my/prefix/key2',
             'Value': 'value2'},
            {'Key': '/my/prefix/key3',
             'Value': 'value3'},
        ]

        result = dict_from_consul('/my/prefix/', consul_dict)

        assert_that(result, has_entries({
            'key1': 'value1',
            'key2': 'value2',
            'key3': 'value3'
        }))

    def test_dict_from_consul_with_unknown_prefix(self):
        consul_dict = [
            {'Key': '/my/prefix/key1',
             'Value': 'value1'}
        ]

        result = dict_from_consul('/unknown/prefix/', consul_dict)

        assert_that(result, equal_to({}))

    def test_dict_from_consul_with_non_ascii(self):
        consul_dict = [
            {'Key': '/my/prefix/key1',
             'Value': 'value1'},
            {'Key': u'/my/prefix/key2',
             'Value': u'vàlùé2'.encode('utf-8')},
            {'Key': '/my/prefix/key3',
             'Value': 'value3'},
        ]

        result = dict_from_consul('/my/prefix/', consul_dict)

        assert_that(result, has_entries({
            'key1': 'value1',
            'key2': u'vàlùé2',
            'key3': 'value3'
        }))

    def test_dict_from_consul_with_value_empty(self):
        consul_dict = [
            {'Key': '/my/prefix/key1',
             'Value': ''},
        ]

        result = dict_from_consul('/my/prefix/', consul_dict)

        assert_that(result, has_entries({
            'key1': '',
        }))

    def test_dict_from_consul_with_value_none(self):
        '''
        Consul transforms empty values to None, so we have to transform them back.
        '''
        consul_dict = [
            {'Key': '/my/prefix/key1',
             'Value': None},
        ]

        result = dict_from_consul('/my/prefix/', consul_dict)

        assert_that(result, has_entries({
            'key1': '',
        }))


class TestLsFromConsul(TestCase):

    def test_ls_from_consul_empty(self):
        result = ls_from_consul('', [])

        assert_that(result, contains())

    def test_ls_from_consul_none(self):
        result = ls_from_consul('', None)

        assert_that(result, contains())

    def test_ls_from_consul_full(self):
        keys = ['/my/prefix/key/attribute1/',
                '/my/prefix/key/attribute2/',
                '/my/prefix/key/attribute3/']

        result = ls_from_consul('/my/prefix/key/', keys)

        assert_that(result, contains('attribute1', 'attribute2', 'attribute3'))

    def test_ls_from_consul_removes_trailing_slashes(self):
        keys = ['/my/prefix/key/attribute1/',
                '/my/prefix/key/attribute2',
                '/my/prefix/key/attribute3///']

        result = ls_from_consul('/my/prefix/key/', keys)

        assert_that(result, contains('attribute1', 'attribute2', 'attribute3'))

    def test_ls_from_consul_with_urlencoded_key(self):
        keys = ['/my/prefix/key/%']

        result = ls_from_consul('/my/prefix/key/', keys)

        assert_that(result, contains('%'))


class TestTreeFromConsul(TestCase):

    def test_tree_from_consul_empty(self):
        result = tree_from_consul('', [])

        assert_that(result, equal_to({}))

    def test_tree_from_consul_entries_none(self):
        result = tree_from_consul('', None)

        assert_that(result, equal_to({}))

    def test_tree_from_consul_prefix_none(self):
        result = tree_from_consul(None, [{'Key': 'key',
                                          'Value': 'value'}])

        assert_that(result, equal_to({'key': 'value'}))

    def test_tree_from_consul_prefix_empty(self):
        result = tree_from_consul('', [{'Key': 'key',
                                        'Value': 'value'}])

        assert_that(result, equal_to({'key': 'value'}))

    def test_tree_from_consul_tranforms_None_values_to_empty_string(self):
        result = tree_from_consul('', [{'Key': 'key',
                                        'Value': None}])

        assert_that(result, equal_to({'key': ''}))

    def test_tree_from_consul_removes_heading_slashes(self):
        result = tree_from_consul('', [{'Key': '//key',
                                        'Value': 'value'}])

        assert_that(result, equal_to({'key': 'value'}))

    def test_tree_from_consul_removes_trailing_slashes(self):
        result = tree_from_consul('', [{'Key': 'key//',
                                        'Value': 'value'}])

        assert_that(result, equal_to({'key': 'value'}))

    def test_tree_from_consul_non_ascii(self):
        result = tree_from_consul('', [{'Key': 'non_ascii_value',
                                        'Value': u'ééé'.encode('utf-8')}])

        assert_that(result, equal_to({'non_ascii_value': u'ééé'}))

    def test_tree_from_consul_one_level(self):
        result = tree_from_consul('my/prefix/', [{'Key': 'my/prefix/key',
                                                  'Value': 'value'},
                                                 {'Key': 'my/prefix/other_key',
                                                  'Value': 'other_value'}])

        assert_that(result, equal_to({'key': 'value',
                                      'other_key': 'other_value'}))

    def test_tree_from_consul_two_levels(self):
        result = tree_from_consul('my/prefix/', [{'Key': 'my/prefix/key/subkey',
                                                  'Value': 'value'},
                                                 {'Key': 'my/prefix/other_key/subkey',
                                                  'Value': 'other_value'}])

        assert_that(result, equal_to({
            'key': {
                'subkey': 'value'
                },
            'other_key': {
                'subkey': 'other_value'
            }
        }))

    def test_tree_from_consul_three_levels(self):
        result = tree_from_consul('my/prefix/', [{'Key': 'my/prefix/key/subkey/subsubkey',
                                                  'Value': 'value'},
                                                 {'Key': 'my/prefix/other_key/subkey/subsubkey',
                                                  'Value': 'other_value'}])

        assert_that(result, equal_to({
            'key': {
                'subkey': {
                    'subsubkey': 'value'
                }
            },
            'other_key': {
                'subkey': {
                    'subsubkey': 'other_value'
                }
            }
        }))


class TestDictToConsul(TestCase):

    def test_that_dict_to_consul_empty(self):
        result = dict_to_consul('', {})

        assert_that(result, equal_to({}))

    def test_dict_to_consul_values_none(self):
        result = dict_to_consul('', None)

        assert_that(result, equal_to({}))

    def test_dict_to_consul_prefix_none(self):
        result = dict_to_consul(None, {'a': 'b'})

        assert_that(result, equal_to({'a': 'b'}))

    def test_dict_to_consul_prefix_empty(self):
        result = dict_to_consul('', {'a': 'b'})

        assert_that(result, equal_to({'a': 'b'}))

    def test_dict_to_consul_full(self):
        consul_dict = {
            'key1': 'value1',
            'key2': 'value2',
            'key3': 'value3'
        }

        result = dict_to_consul('/my/prefix/', consul_dict)

        assert_that(result, has_entries({
            '/my/prefix/key1': 'value1',
            '/my/prefix/key2': 'value2',
            '/my/prefix/key3': 'value3'
        }))

    def test_dict_to_consul_non_ascii(self):
        consul_dict = {
            'key': u'non_ascii_value_ééé'
        }

        result = dict_to_consul(u'prefix/', consul_dict)

        assert_that(result, has_entries({
            u'prefix/key': 'non_ascii_value_ééé',
        }))

    def test_dict_to_consul_special_characters(self):
        consul_dict = {
            u'%?#': 'value1',
        }

        result = dict_to_consul(u'%?#/', consul_dict)

        assert_that(result, has_entries({
            '%25%3F%23/%25%3F%23': 'value1'
        }))
