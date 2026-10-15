# Copyright 2015-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest.mock import patch

from hamcrest import assert_that, calling, equal_to, raises

from wazo_dird.helpers import RaiseStopper, timed


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


class TestTimed(unittest.TestCase):
    def test_that_the_result_is_returned(self):
        result, _ = timed(_ok, 1, 2)

        assert_that(result, equal_to(2))

    def test_that_keyword_arguments_are_forwarded(self):
        result, _ = timed(lambda *, value: [value], value='a')

        assert_that(result, equal_to(['a']))

    @patch('wazo_dird.helpers.time.monotonic', side_effect=[10.0, 12.5])
    def test_that_the_elapsed_seconds_are_returned(self, _monotonic):
        _, duration = timed(_ok, 1, 2)

        assert_that(duration, equal_to(2.5))

    def test_that_exceptions_are_propagated(self):
        assert_that(calling(timed).with_args(_throwing), raises(AssertionError))
