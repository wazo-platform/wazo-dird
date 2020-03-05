# Copyright 2019-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase

from hamcrest import (
    assert_that,
    calling,
    equal_to,
    has_entry,
    has_item,
    has_items,
    not_,
    raises,
)

from ..plugin import Office365Plugin


class TestOffice365Plugin(TestCase):

    DEPENDENCIES = {
        'config': {
            'auth': {'host': '9497'},
            'endpoint': 'www.bros.com',
            'name': 'office365',
            'user_agent': 'luigi',
            'first_matched_columns': ['mobilePhone', 'businessPhones'],
            'format_columns': {
                'display_name': "{firstname} {lastname}",
                'name': "{firstname} {lastname}",
                'reverse': "{firstname} {lastname}",
                'phone_mobile': "{mobilePhone}",
            },
        }
    }

    def setUp(self):
        self.source = Office365Plugin()

    def test_load(self):
        assert_that(
            calling(self.source.load).with_args(self.DEPENDENCIES),
            not_(raises(Exception)),
        )

    def test_first_match_predicate(self):
        self.source.load(self.DEPENDENCIES)

        term = '5555551234'

        mario = {'name': 'Mario Bros', 'mobilePhone': None, 'businessPhones': []}
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
        assert_that(
            self.source._first_match_predicate(term[:-1], peach), equal_to(False)
        )

    def test_update_contact_fields_all_phones(self):
        self.source.load(self.DEPENDENCIES)

        mario = {
            'name': 'Mario Bros',
            'mobilePhone': '1234',
            'businessPhones': ['567', '890'],
            'homePhones': ['111'],
        }

        assert_that(
            self.source._update_contact_fields([mario]),
            has_item(has_entry('numbers', has_items('1234', '567', '890', '111'))),
        )

    def test_update_contact_fields_one_phone(self):
        self.source.load(self.DEPENDENCIES)

        mario = {
            'name': 'Mario Bros',
            'mobilePhone': None,
            'businessPhones': [],
            'homePhones': ['111'],
        }

        assert_that(
            self.source._update_contact_fields([mario]),
            has_item(has_entry('numbers', has_item('111'))),
        )
