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

from hamcrest import assert_that
from hamcrest import equal_to
from hamcrest import has_entries
from hamcrest import none
from mock import sentinel
from xivo_dird.plugins.source_result import _SourceResult
from xivo_dird.plugins.source_result import make_result_class


class TestSourceResult(unittest.TestCase):

    def setUp(self):
        self.xivo_id = sentinel.xivo_id
        self.fields = {'client_no': 1, 'firstname': 'fn', 'lastname': 'ln'}
        self.empty_relations = {
            'xivo_id': self.xivo_id,
            'agent_id': None,
            'user_id': None,
            'endpoint_id': None,
        }

    def test_source(self):
        r = _SourceResult(self.fields, self.xivo_id)
        r.source = sentinel.source

        assert_that(r.source, equal_to(sentinel.source))

    def test_fields(self):
        r = _SourceResult(self.fields, self.xivo_id)

        assert_that(r.fields, equal_to(self.fields))
        assert_that(r.relations, equal_to(self.empty_relations))

    def test_agent_relation(self):
        r = _SourceResult(self.fields, self.xivo_id, agent_id=sentinel.agent_id)

        assert_that(r.relations, equal_to({'xivo_id': sentinel.xivo_id,
                                           'agent_id': sentinel.agent_id,
                                           'user_id': None,
                                           'endpoint_id': None}))

    def test_user_relation(self):
        r = _SourceResult(self.fields, sentinel.xivo_id, user_id=sentinel.user_id)

        assert_that(r.relations, equal_to({'xivo_id': sentinel.xivo_id,
                                           'agent_id': None,
                                           'user_id': sentinel.user_id,
                                           'endpoint_id': None}))

    def test_endpoint_relation(self):
        r = _SourceResult(self.fields, sentinel.xivo_id, endpoint_id=sentinel.endpoint_id)

        assert_that(r.relations, equal_to({'xivo_id': sentinel.xivo_id,
                                           'agent_id': None,
                                           'user_id': None,
                                           'endpoint_id': sentinel.endpoint_id}))

    def test_get_unique(self):
        r = _SourceResult(self.fields)
        r._unique_column = 'client_no'

        assert_that(r.get_unique(), equal_to('1'))

    def test_that_source_to_dest_transformation_are_applied(self):
        SourceResult = make_result_class(sentinel.name, source_to_dest_map={'firstname': 'fn',
                                                                            'lastname': 'ln'})

        r = SourceResult(self.fields)

        assert_that(r.fields, has_entries('fn', 'fn', 'ln', 'ln'))


class TestMakeResultClass(unittest.TestCase):

    def test_source_name(self):
        SourceResult = make_result_class(sentinel.source_name)

        s = SourceResult(sentinel.fields)

        assert_that(s.source, equal_to(sentinel.source_name))

    def test_source_unique_column(self):
        SourceResult = make_result_class(sentinel.source_name, sentinel.unique_column)

        s = SourceResult(sentinel.fields)

        assert_that(s._unique_column, equal_to(sentinel.unique_column))
        assert_that(s._source_to_dest_map, equal_to({}))

    def test_source_to_destination(self):
        SourceResult = make_result_class(sentinel.source_name,
                                         source_to_dest_map={'from': 'to'})

        s = SourceResult({})

        assert_that(s._source_to_dest_map, equal_to({'from': 'to'}))
        assert_that(s._unique_column, none())
