# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase

from hamcrest import (
    assert_that,
    calling,
    equal_to,
    not_,
    raises,
)

from ..plugin import GooglePlugin


class TestGooglePlugin(TestCase):

    DEPENDENCIES = {
        'config': {
            'auth': {
                'host': '9497',
            },
            'name': 'google',
            'user_agent': 'luigi',
            'first_matched_columns': ['numbers'],
            'format_columns': {
                'display_name': "{name}",
                'reverse': "{name}",
                'phone_mobile': "{numbers_by_label[mobile]}",
                'phone': '{numbers[0]}',
            },
        },
    }

    def setUp(self):
        self.source = GooglePlugin()

    def test_load(self):
        assert_that(
            calling(self.source.load).with_args(self.DEPENDENCIES),
            not_(raises(Exception))
        )

    def test_first_match_predicate(self):
        self.source.load(self.DEPENDENCIES)

        term = '5555551234'

        mario = {
            'name': 'Mario Bros',
            'numbers': {},
        }
        luigi = {
            'name': 'Luigi Bros',
            'numbers_by_label': {'mobile': '5555551234'},
            'numbers': ['5555551234'],
        }
        peach = {
            'name': 'Peach',
            'numbers_by_label': {
                'mobile': '5555551234',
                'business': '4185553212',
            },
            'numbers': [
                '5555551234',
                '4185553212',
            ],
        }

        assert_that(self.source._first_match_predicate(term, mario), equal_to(False))
        assert_that(self.source._first_match_predicate(term, luigi), equal_to(True))
        assert_that(self.source._first_match_predicate(term, peach), equal_to(True))
        assert_that(self.source._first_match_predicate(term[:-1], peach), equal_to(False))
