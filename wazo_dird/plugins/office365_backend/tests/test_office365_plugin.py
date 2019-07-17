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

from ..plugin import Office365Plugin


class TestOffice365Plugin(TestCase):

    DEPENDENCIES = {
        'config': {
            'auth': {
                'host': '9497',
            },
            'endpoint': 'www.bros.com',
            'name': 'office365',
            'user_agent': 'luigi',
            'first_matched_columns': ['mobilePhone', 'businessPhones'],
            'format_columns': {
                'display_name': "{firstname} {lastname}",
                'name': "{firstname} {lastname}",
                'reverse': "{firstname} {lastname}",
                'phone_mobile': "{mobile}",
            },
        },
    }

    def setUp(self):
        self.source = Office365Plugin()

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
            'mobilePhone': None,
            'businessPhones': [],
        }
        luigi = {
            'name': 'Luigi Bros',
            'mobilePhone': None,
            'businessPhones': ['5555551234'],
        }
        peach = {
            'name': 'Peach',
            'mobilePhone': '5555551234',
            'businessPhones': ['4185553212'],
        }

        assert_that(self.source._first_match_predicate(term, mario), equal_to(False))
        assert_that(self.source._first_match_predicate(term, luigi), equal_to(True))
        assert_that(self.source._first_match_predicate(term, peach), equal_to(True))
        assert_that(self.source._first_match_predicate(term[:-1], peach), equal_to(False))
