# -*- coding: utf-8 -*-
#
# Copyright 2016-2017 The Wazo Authors  (see the AUTHORS file)
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

from hamcrest import assert_that, calling, equal_to, raises
from mock import Mock, patch, sentinel as s

from xivo_dird.exception import InvalidConfigError

from ..dird_phonebook import PhonebookPlugin, make_result_class


class TestDirdPhonebook(unittest.TestCase):

    def setUp(self):
        self.source = PhonebookPlugin()
        self.SourceResult = self.source._SourceResult = make_result_class('test', 'id', {})
        self.engine = self.source._search_engine = Mock()

    def test_get_phonebook_id_unknown_phonebook(self):
        with patch.object(self.source, '_crud', Mock(list=Mock(return_value=[]))):
            assert_that(calling(self.source._get_phonebook_id).with_args({'phonebook_name': 'unknown'}),
                        raises(InvalidConfigError))

    def test_that_the_id_is_used_if_supplied(self):
        id_ = self.source._get_phonebook_id({'phonebook_id': 42})

        assert_that(id_, equal_to(42))

    def test_with_an_existing_phonebook_by_name(self):
        phonebooks = [{'id': 1, 'name': 'foo'}, {'id': 2, 'name': 'bar'}]

        with patch.object(self.source, '_crud', Mock(list=Mock(return_value=phonebooks))):
            id_ = self.source._get_phonebook_id({'phonebook_name': 'bar'})

        assert_that(id_, equal_to(2))

    def test_that_find_first_returns_a_formated_result(self):
        raw_result = self.engine.find_first_contact.return_value = {'id': 42,
                                                                    'name': 'foobar'}

        result = self.source.first_match(s.term)

        assert_that(result, equal_to(self.SourceResult(raw_result)))

    def test_that_find_first_returns_none_when_empty_result(self):
        self.engine.find_first_contact.return_value = None

        result = self.source.first_match(s.term)

        assert_that(result, equal_to(None))
