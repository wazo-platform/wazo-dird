# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    contains_exactly,
    contains_inanyorder,
    contains_string,
    has_entry,
    not_,
)

from .helpers.base import BaseDirdIntegrationTest
from .helpers.config import Config

_SLOW_WS_URL = 'http://ws:9485/ws'
_SLOW_WS_CONTACT_ID = 'slow-1'
_FAST_CSV_CONTACT_ID = 'fast-1'

_DEFAULT_DISPLAY = {
    'name': 'default_display',
    'columns': [
        {'title': 'Firstname', 'field': 'firstname'},
        {'title': 'Lastname', 'field': 'lastname'},
    ],
}


def new_favorites_timeout_config(Session):
    config = Config(Session)
    config.with_display(**_DEFAULT_DISPLAY)
    config.with_source(
        backend='csv_ws',
        name='slow_ws',
        lookup_url=_SLOW_WS_URL,
        list_url=_SLOW_WS_URL,
        unique_column='id',
    )
    config.with_source(
        backend='csv',
        name='fast_csv',
        file='/tmp/data/fast.csv',
        separator=',',
        unique_column='id',
    )
    config.with_profile(
        name='favorites-short-timeout',
        display='default_display',
        services={
            'favorites': {
                'sources': ['slow_ws', 'fast_csv'],
                'options': {'timeout': 0.5},
            }
        },
    )
    config.with_profile(
        name='favorites-long-timeout',
        display='default_display',
        services={
            'favorites': {
                'sources': ['slow_ws', 'fast_csv'],
                'options': {'timeout': 5},
            }
        },
    )
    config.with_profile(
        name='favorites-no-options',
        display='default_display',
        services={'favorites': {'sources': ['slow_ws', 'fast_csv']}},
    )
    config.with_profile(
        name='favorites-null-timeout',
        display='default_display',
        services={
            'favorites': {
                'sources': ['slow_ws', 'fast_csv'],
                'options': {'timeout': None},
            }
        },
    )
    return config


class TestFavoritesServiceTimeout(BaseDirdIntegrationTest):
    """
    Verify that options.timeout on a favorites profile is honoured.

    The 'ws' service sleeps 2s before responding. A profile with
    options.timeout=0.5 must return only the fast source's favorite;
    one with options.timeout=5 must return both.
    """

    asset = 'favorites_timeout'
    config_factory = new_favorites_timeout_config

    def test_short_timeout_returns_only_the_fast_source(self) -> None:
        with self.favorite('fast_csv', _FAST_CSV_CONTACT_ID), self.favorite(
            'slow_ws', _SLOW_WS_CONTACT_ID
        ):
            with self.capture_logs(service_name='dird') as logs:
                result = self.favorites('favorites-short-timeout')

        assert_that(
            result['results'],
            contains_exactly(
                has_entry('column_values', contains_exactly('Bob', 'Fast'))
            ),
        )
        assert_that(logs.result(), contains_string("incomplete=['slow_ws']"))

    def test_long_timeout_returns_every_source(self) -> None:
        with self.favorite('fast_csv', _FAST_CSV_CONTACT_ID), self.favorite(
            'slow_ws', _SLOW_WS_CONTACT_ID
        ):
            result = self.favorites('favorites-long-timeout')

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entry('column_values', contains_exactly('Bob', 'Fast')),
                has_entry('column_values', contains_exactly('Alice', 'Timeout')),
            ),
        )

    def test_no_options_waits_for_the_slow_source(self) -> None:
        self._assert_exhaustive('favorites-no-options')

    def test_null_timeout_waits_for_the_slow_source(self) -> None:
        self._assert_exhaustive('favorites-null-timeout')

    def _assert_exhaustive(self, profile: str) -> None:
        """A profile with no timeout must return every source, however slow."""
        with self.favorite('fast_csv', _FAST_CSV_CONTACT_ID), self.favorite(
            'slow_ws', _SLOW_WS_CONTACT_ID
        ):
            with self.capture_logs(service_name='dird') as logs:
                result = self.favorites(profile)

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entry('column_values', contains_exactly('Bob', 'Fast')),
                has_entry('column_values', contains_exactly('Alice', 'Timeout')),
            ),
        )
        assert_that(logs.result(), not_(contains_string('incomplete=')))
