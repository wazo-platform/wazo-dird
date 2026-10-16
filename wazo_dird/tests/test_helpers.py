# Copyright 2015-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import unittest
from concurrent.futures import Future
from unittest.mock import patch

from hamcrest import assert_that, calling, equal_to, raises

from wazo_dird.helpers import (
    BackendStat,
    RaiseStopper,
    Timing,
    log_backend_stats,
    timed,
)


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
        result, _ = timed(0.0, _ok, 1, 2)

        assert_that(result, equal_to(2))

    def test_that_keyword_arguments_are_forwarded(self):
        result, _ = timed(0.0, lambda *, value: [value], value='a')

        assert_that(result, equal_to(['a']))

    @patch('wazo_dird.helpers.perf_counter', side_effect=[11.0, 12.5])
    def test_that_queue_and_execution_seconds_are_returned_separately(self, _clock):
        _, timing = timed(10.0, _ok, 1, 2)

        assert_that(timing, equal_to(Timing(queue=1.0, execution=1.5)))

    def test_that_exceptions_are_propagated(self):
        assert_that(calling(timed).with_args(0.0, _throwing), raises(AssertionError))


def _named_future(name: str) -> Future:
    future: Future = Future()
    setattr(future, 'name', name)
    return future


class TestBackendStatUnfinished(unittest.TestCase):
    def test_that_a_future_never_started_is_queued(self):
        future = _named_future('ldap')

        assert_that(BackendStat.from_future(future).status, equal_to('queued'))

    def test_that_a_future_being_executed_is_running(self):
        future = _named_future('ldap')
        future.set_running_or_notify_cancel()

        assert_that(BackendStat.from_future(future).status, equal_to('running'))

    def test_that_a_cancelled_future_is_cancelled(self):
        future = _named_future('ldap')
        future.cancel()

        assert_that(BackendStat.from_future(future).status, equal_to('cancelled'))

    def test_that_the_source_name_is_kept(self):
        assert_that(
            BackendStat.from_future(_named_future('ldap')).name, equal_to('ldap')
        )


class TestLogBackendStats(unittest.TestCase):
    LOGGER = 'wazo_dird.test.timing'

    def test_that_finished_and_unfinished_backends_are_logged(self):
        stats = [
            BackendStat.finished('fast', 2, Timing(queue=0.0005, execution=0.0125)),
            BackendStat('slow', 'running'),
            BackendStat('late', 'cancelled'),
        ]

        with self.assertLogs(self.LOGGER, level='DEBUG') as logs:
            log_backend_stats(logging.getLogger(self.LOGGER), 'lookup', stats)

        assert_that(
            logs.records[0].getMessage(),
            equal_to(
                'lookup per-backend latency: '
                'fast status=done results=2 queue_ms=0.5 exec_ms=12.5, '
                'slow status=running, late status=cancelled'
            ),
        )
        assert_that(logs.records[0].levelname, equal_to('DEBUG'))

    def test_that_nothing_is_logged_above_debug(self):
        log = logging.getLogger(self.LOGGER)

        with self.assertNoLogs(log, level='INFO'):
            log_backend_stats(
                log, 'lookup', [BackendStat.finished('a', 1, Timing(0.0, 0.1))]
            )
