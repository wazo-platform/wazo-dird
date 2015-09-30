# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Avencall
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

from xivo_dird.helpers import no_throw_execute


def _ok(ignored, returned):
    return returned


def _throwing():
    raise AssertionError('Should not happen')


class TestNoThrowExecute(unittest.TestCase):

    def test_that_the_result_is_returned(self):
        result = no_throw_execute(None, _ok, 1, 2)

        assert_that(result, equal_to(2))

    def test_that_exceptions_are_consumed(self):
        no_throw_execute(None, _throwing)

    def test_that_the_default_return_value_is_used_for_exceptions(self):
        result = no_throw_execute(['one', 'two'], _throwing)

        assert_that(result, equal_to(['one', 'two']))
