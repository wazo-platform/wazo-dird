# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    contains_exactly,
    contains_inanyorder,
    contains_string,
    equal_to,
    has_entries,
    has_entry,
    none,
    not_,
)

from .helpers.base import BaseDirdIntegrationTest
from .helpers.config import Config
from .helpers.constants import VALID_UUID

_SLOW_WS_URL = 'http://ws:9485/ws'
_SLOW_WS_NUMBER = '5551234567'
_SLOW_WS_CONTACT_ID = 'slow-1'
_FAST_CSV_NUMBER = '5559999999'
_FAST_CSV_CONTACT_ID = 'fast-1'

_DEFAULT_DISPLAY = {
    'name': 'default_display',
    'columns': [
        {'title': 'Firstname', 'field': 'firstname'},
        {'title': 'Lastname', 'field': 'lastname'},
    ],
}


def new_service_timeout_config(Session):
    config = Config(Session)
    config.with_display(**_DEFAULT_DISPLAY)
    config.with_source(
        backend='csv_ws',
        name='slow_ws',
        lookup_url=_SLOW_WS_URL,
        list_url=_SLOW_WS_URL,
        unique_column='id',
        first_matched_columns=['number'],
        format_columns={'reverse': '{firstname} {lastname}'},
    )
    config.with_source(
        backend='csv',
        name='fast_csv',
        file='/tmp/data/fast.csv',
        separator=',',
        unique_column='id',
        first_matched_columns=['number'],
        format_columns={'reverse': '{firstname} {lastname}'},
    )
    config.with_profile(
        name='reverse-short-timeout',
        display='default_display',
        services={
            'reverse': {
                'sources': ['slow_ws'],
                'options': {'timeout': 0.1},
            }
        },
    )
    config.with_profile(
        name='reverse-long-timeout',
        display='default_display',
        services={
            'reverse': {
                'sources': ['slow_ws'],
                'options': {'timeout': 5},
            }
        },
    )
    config.with_profile(
        name='reverse-many-short-timeout',
        display='default_display',
        services={
            'reverse': {
                'sources': ['slow_ws', 'fast_csv'],
                'options': {'timeout': 0.1},
            }
        },
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


class TestServiceTimeout(BaseDirdIntegrationTest):
    """
    Verify that a profile's options.timeout is honoured by each service.

    The 'ws' service sleeps 2s before it answers. A profile with a timeout
    shorter than that delay must return partial results; a profile with a
    longer timeout, or with no timeout at all, must return every source.
    """

    asset = 'service_timeout'
    config_factory = new_service_timeout_config

    def test_reverse_with_short_timeout_returns_no_result(self) -> None:
        result = self.reverse(_SLOW_WS_NUMBER, 'reverse-short-timeout', VALID_UUID)

        assert_that(result['display'], none())

    def test_reverse_with_long_timeout_returns_contact(self) -> None:
        result = self.reverse(_SLOW_WS_NUMBER, 'reverse-long-timeout', VALID_UUID)

        assert_that(result['display'], not_(none()))
        assert_that(result['display'], equal_to('Alice Timeout'))

    def test_reverse_many_with_short_timeout_returns_partial_and_logs_incomplete_source(
        self,
    ) -> None:
        query = {
            'query': '''
            {
                me {
                    contacts(
                        profile: "reverse-many-short-timeout",
                        extens: ["%s", "%s"]
                    ) {
                        edges {
                            node {
                                firstname
                            }
                        }
                    }
                }
            }
            '''
            % (_FAST_CSV_NUMBER, _SLOW_WS_NUMBER),
        }

        with self.capture_logs(service_name='dird') as logs:
            response = self.dird.graphql.query(query)

        assert_that(
            response['data']['me']['contacts']['edges'],
            contains_exactly(
                has_entry('node', has_entries({'firstname': 'Bob'})),
                has_entry('node', none()),
            ),
        )
        assert_that(logs.result(), contains_string('incomplete=[\'slow_ws\']'))

    def test_favorites_with_short_timeout_returns_only_the_fast_source(self) -> None:
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

    def test_favorites_with_long_timeout_returns_every_source(self) -> None:
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

    def test_favorites_with_no_options_waits_for_the_slow_source(self) -> None:
        self._assert_favorites_exhaustive('favorites-no-options')

    def test_favorites_with_null_timeout_waits_for_the_slow_source(self) -> None:
        self._assert_favorites_exhaustive('favorites-null-timeout')

    def _assert_favorites_exhaustive(self, profile: str) -> None:
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
