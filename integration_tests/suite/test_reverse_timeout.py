# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    contains,
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

_SLOW_WS_NUMBER = '5551234567'
_SLOW_WS_URL = 'http://ws:9485/ws'
_FAST_CSV_NUMBER = '5559999999'

_DEFAULT_DISPLAY = {
    'name': 'default_display',
    'columns': [
        {'title': 'Firstname', 'field': 'firstname'},
        {'title': 'Lastname', 'field': 'lastname'},
    ],
}


def new_reverse_timeout_config(Session):
    config = Config(Session)
    config.with_display(**_DEFAULT_DISPLAY)
    config.with_source(
        backend='csv_ws',
        name='slow_ws',
        lookup_url=_SLOW_WS_URL,
        list_url=_SLOW_WS_URL,
        first_matched_columns=['number'],
        format_columns={'reverse': '{firstname} {lastname}'},
    )
    config.with_source(
        backend='csv',
        name='fast_csv',
        file='/tmp/data/fast.csv',
        separator=',',
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
    return config


class TestReverseServiceTimeout(BaseDirdIntegrationTest):
    """
    Verify that options.timeout on a reverse profile is honoured.

    The 'ws' service sleeps 2s before responding. A profile with
    options.timeout=0.1 must time out (return None); one with
    options.timeout=5 must return the contact.
    """

    asset = 'reverse_timeout'
    config_factory = new_reverse_timeout_config

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
            contains(
                has_entry('node', has_entries({'firstname': 'Bob'})),
                has_entry('node', none()),
            ),
        )
        assert_that(logs.result(), contains_string('incomplete=[\'slow_ws\']'))
