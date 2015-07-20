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
from mock import Mock
from mock import patch
from unittest import TestCase

from ..privates_backend import PrivatesBackend


class TestPrivatesBackend(TestCase):

    @patch('xivo_dird.plugins.privates_backend.Consul')
    def test_that_list_calls_consul_get(self, consul_init):
        consul = consul_init.return_value
        consul.kv.get.return_value = Mock(), []
        source = PrivatesBackend()
        source.load({'config': {'name': 'privates'},
                     'main_config': {'consul': {'host': 'localhost'}}})

        source.list(['1', '2'], {'token': 'valid-token', 'auth_id': 'my-uuid'})

        assert_that(consul.kv.get.call_count, greater_than(1))
