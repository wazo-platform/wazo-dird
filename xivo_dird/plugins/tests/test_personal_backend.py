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
from hamcrest import greater_than
from hamcrest import has_item
from hamcrest import has_property
from mock import Mock
from mock import patch
from unittest import TestCase

from ..personal_backend import PersonalBackend


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

        source.search('alice', {'token_infos': {'token': 'valid-token', 'auth_id': 'my-uuid'}})

        assert_that(consul.kv.get.call_count, greater_than(0))
