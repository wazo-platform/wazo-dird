# Copyright (C) 2015 Avencall
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from hamcrest import assert_that
from hamcrest import equal_to

from wazo_dird.helpers import RaiseStopper


def _ok(ignored, returned):
    return returned


def _throwing():
    raise AssertionError('Should not happen')


class TestNoThrowExecute(unittest.TestCase):
    def test_that_the_result_is_returned(self):
        result = RaiseStopper(return_on_raise=None).execute(_ok, 1, 2)

        assert_that(result, equal_to(2))

    def test_that_exceptions_are_consumed(self):
        RaiseStopper(return_on_raise=None).execute(_throwing)

    def test_that_the_default_return_value_is_used_for_exceptions(self):
        result = RaiseStopper(return_on_raise=['one', 'two']).execute(_throwing)

        assert_that(result, equal_to(['one', 'two']))
