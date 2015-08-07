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
            {'Key': u'/my/prefix/kéỳ2',
             'Value': u'vàlùé2'.encode('utf-8')},
            {'Key': '/my/prefix/key3',
             'Value': 'value3'},
        ]

        result = dict_from_consul('/my/prefix/', consul_dict)

        assert_that(result, has_entries({
            'key1': 'value1',
            u'kéỳ2': u'vàlùé2',
            'key3': 'value3'
        }))

    def test_dict_from_consul_with_value_empty(self):
        consul_dict = [
            {'Key': '/my/prefix/key1',
             'Value': ''},
        ]

        result = dict_from_consul('/my/prefix/', consul_dict)

        assert_that(result, has_entries({
            'key1': None,
        }))

    def test_dict_from_consul_with_value_none(self):
        consul_dict = [
            {'Key': '/my/prefix/key1',
             'Value': None},
        ]

        result = dict_from_consul('/my/prefix/', consul_dict)

        assert_that(result, has_entries({
            'key1': None,
        }))

    def test_dict_from_consul_with_urlencoded_key(self):
        consul_dict = [
            {'Key': '/my/prefix/%25',
             'Value': 'value'},
        ]

        result = dict_from_consul('/my/prefix/', consul_dict)

        assert_that(result, has_entries({
            '%': 'value',
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

    def test_ls_from_consul_with_non_ascii(self):
        keys = ['/my/prefix/key/attribute1',
                u'/my/prefix/key/àttríbùté2'.encode('utf-8'),
                '/my/prefix/key/attribute3']

        result = ls_from_consul('/my/prefix/key/', keys)

        assert_that(result, contains('attribute1', u'àttríbùté2', 'attribute3'))

    def test_ls_from_consul_with_urlencoded_key(self):
        keys = ['/my/prefix/key/%25']

        result = ls_from_consul('/my/prefix/key/', keys)

        assert_that(result, contains('%'))


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
            u'non_ascii_key_ééé': 'value1',
            'key2': u'non_ascii_value_ééé'
        }

        result = dict_to_consul(u'non_ascii_prefix_ééé/', consul_dict)

        assert_that(result, has_entries({
            u'non_ascii_prefix_%C3%A9%C3%A9%C3%A9/non_ascii_key_%C3%A9%C3%A9%C3%A9': 'value1',
            u'non_ascii_prefix_%C3%A9%C3%A9%C3%A9/key2': 'non_ascii_value_ééé',
        }))

    def test_dict_to_consul_special_characters(self):
        consul_dict = {
            u'%?#': 'value1',
        }

        result = dict_to_consul(u'%?#/', consul_dict)

        assert_that(result, has_entries({
            '%25%3F%23/%25%3F%23': 'value1'
        }))