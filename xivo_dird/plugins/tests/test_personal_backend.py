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
from hamcrest import equal_to
from hamcrest import greater_than
from hamcrest import has_item
from hamcrest import has_property
from hamcrest import not_
from mock import Mock
from mock import patch
from unittest import TestCase

from ..personal_backend import match
from ..personal_backend import PersonalBackend
from ..personal_backend import remove_empty_values


class TestPersonalBackend(TestCase):

    @patch('xivo_dird.plugins.personal_backend.Consul')
    def test_that_list_calls_consul_get(self, consul_init):
        consul = consul_init.return_value
        consul.kv.get.return_value = Mock(), []
        source = PersonalBackend()
        source.load({'config': {'name': 'personal'},
                     'main_config': {'consul': {'host': 'localhost'}}})

        source.list(['1', '2'], {'token_infos': {'token': 'valid-token', 'auth_id': 'my-uuid'}})

        assert_that(consul.kv.get.call_count, greater_than(1))

    @patch('xivo_dird.plugins.personal_backend.Consul')
    def test_that_list_sets_attribute_personal_and_deletable(self, consul_init):
        consul = consul_init.return_value
        consul.kv.get.return_value = Mock(), [{'Key': 'my/key',
                                               'Value': 'my-value'}]
        source = PersonalBackend()
        source.load({'config': {'name': 'personal'},
                     'main_config': {'consul': {'host': 'localhost'}}})

        result = source.list(['1'], {'token_infos': {'token': 'valid-token', 'auth_id': 'my-uuid'}})

        assert_that(result, has_item(has_property('is_personal', True)))
        assert_that(result, has_item(has_property('is_deletable', True)))

    @patch('xivo_dird.plugins.personal_backend.Consul')
    def test_that_search_calls_consul_get(self, consul_init):
        consul = consul_init.return_value
        consul.kv.get.return_value = Mock(), []
        source = PersonalBackend()
        source.load({'config': {'name': 'personal'},
                     'main_config': {'consul': {'host': 'localhost'}}})

        source.search('alice', {'token': 'valid-token', 'auth_id': 'my-uuid'})

        assert_that(consul.kv.get.call_count, greater_than(0))

    @patch('xivo_dird.plugins.personal_backend.Consul')
    def test_that_first_match_calls_consul_get(self, consul_init):
        consul = consul_init.return_value
        consul.kv.get.return_value = Mock(), []
        source = PersonalBackend()
        source.load({'config': {'name': 'personal'},
                     'main_config': {'consul': {'host': 'localhost'}}})

        source.first_match('555', {'token': 'valid-token', 'auth_id': 'my-uuid'})

        assert_that(consul.kv.get.call_count, greater_than(0))

    @patch('xivo_dird.plugins.personal_backend.Consul')
    def test_that_first_match_return_none_if_no_match(self, consul_init):
        consul = consul_init.return_value
        consul.kv.get.return_value = Mock(), []
        source = PersonalBackend()
        source.load({'config': {'name': 'personal'},
                     'main_config': {'consul': {'host': 'localhost'}}})

        result = source.first_match('555', {'token': 'valid-token', 'auth_id': 'my-uuid'})

        assert_that(result, equal_to(None))


class TestMatch(TestCase):

    def test_that_empty_strings_match(self):
        assert_that(match(u'', u''))

    def test_that_empty_string_matches_non_empty(self):
        assert_that(match(u'', u'a'))

    def test_that_different_string_dont_match(self):
        assert_that(not_(match(u'a', u'b')))

    def test_that_substring_matches_superstring(self):
        assert_that(not_(match(u'abc', u'zabcd')))

    def test_that_lowercase_matches_uppercase(self):
        assert_that(not_(match(u'abc', u'ZABCD')))
        assert_that(not_(match(u'ABC', u'zabcd')))

    def test_that_non_ascii_matches_ascii(self):
        assert_that(not_(match(u'café', u'cafe')))
        assert_that(not_(match(u'cafe', u'café')))


class TestRemoveEmptyValues(TestCase):

    def test_that_remove_empty_values_empty_returns_empty(self):
        result = remove_empty_values({})

        assert_that(result, equal_to({}))

    def test_that_remove_empty_values_non_empty_returns_input(self):
        result = remove_empty_values({'a': 'b', 'c': 'd'})

        assert_that(result, equal_to({'a': 'b', 'c': 'd'}))

    def test_that_remove_empty_values_with_empty_values_removes_empty_values(self):
        result = remove_empty_values({'a': 'b', 'c': ''})

        assert_that(result, equal_to({'a': 'b'}))
