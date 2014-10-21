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

from hamcrest import assert_that
from hamcrest import equal_to
from mock import sentinel
from xivo_dird import SourceResult


class TestSourceResult(unittest.TestCase):

    def setUp(self):
        self.fields = {'firstname': 'fn', 'lastname': 'ln'}
        self.empty_relations = {
            'agent': None,
            'user': None,
            'endpoint': None,
        }

    def test_source(self):
        r = SourceResult(self.fields, sentinel.source)

        assert_that(r.source, equal_to(sentinel.source))

    def test_fields(self):
        r = SourceResult(self.fields, sentinel.source)

        assert_that(r.fields, equal_to(self.fields))
        assert_that(r.relations, equal_to(self.empty_relations))

    def test_agent_relation(self):
        r = SourceResult(self.fields, sentinel.source, sentinel.xivo_id, agent_id=sentinel.agent_id)

        assert_that(r.relations, equal_to({'agent': {'id': sentinel.agent_id,
                                                     'xivo_id': sentinel.xivo_id},
                                           'user': None,
                                           'endpoint': None}))

    def test_user_relation(self):
        r = SourceResult(self.fields, sentinel.source, sentinel.xivo_id, user_id=sentinel.user_id)

        assert_that(r.relations, equal_to({'agent': None,
                                           'user': {'id': sentinel.user_id,
                                                    'xivo_id': sentinel.xivo_id},
                                           'endpoint': None}))

    def test_endpoint_relation(self):
        r = SourceResult(self.fields, sentinel.source,
                         sentinel.xivo_id, endpoint_id=sentinel.endpoint_id)

        assert_that(r.relations, equal_to({'agent': None,
                                           'user': None,
                                           'endpoint': {'id': sentinel.endpoint_id,
                                                        'xivo_id': sentinel.xivo_id}}))
