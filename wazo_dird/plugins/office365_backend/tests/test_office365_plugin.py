# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import copy
from typing import Any
from unittest import TestCase
from unittest.mock import Mock, patch

from hamcrest import (
    assert_that,
    calling,
    contains_exactly,
    contains_inanyorder,
    empty,
    equal_to,
    has_entries,
    has_item,
    has_items,
    not_,
    raises,
)

from wazo_dird.exception import SourceListError

from ..exceptions import MicrosoftTokenNotFoundException, UnexpectedEndpointException
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

        mario: dict[str, Any] = {
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
            has_item(
                has_entries(
                    {
                        'numbers': has_items('1234', '567', '890', '111'),
                        'numbers_except_label': has_entries(
                            {
                                'mobilePhone': contains_inanyorder('567', '890', '111'),
                                'businessPhones': contains_inanyorder('1234', '111'),
                                'homePhones': contains_inanyorder('1234', '567', '890'),
                            }
                        ),
                    }
                )
            ),
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
            has_item(
                has_entries(
                    {
                        'numbers': has_item('111'),
                        'numbers_except_label': has_entries(
                            {
                                'mobilePhone': contains_inanyorder('111'),
                                'businessPhones': contains_inanyorder('111'),
                                'homePhones': empty(),
                            }
                        ),
                    }
                )
            ),
        )

    def test_update_contact_fields_no_phone(self):
        self.source.load(self.DEPENDENCIES)

        mario: dict[str, Any] = {
            'name': 'Mario Bros',
            'mobilePhone': None,
            'businessPhones': [],
            'homePhones': [],
        }

        assert_that(
            self.source._update_contact_fields([mario]),
            has_item(
                has_entries(
                    {
                        'numbers': empty(),
                        'numbers_except_label': has_entries(
                            {
                                'mobilePhone': empty(),
                                'businessPhones': empty(),
                                'homePhones': empty(),
                            }
                        ),
                    }
                )
            ),
        )


class TestOffice365PluginListAll(TestCase):
    ARGS = {'token': 'wazo-token', 'user_uuid': 'user-uuid'}

    def setUp(self):
        self.source = Office365Plugin()
        self.source.load(copy.deepcopy(TestOffice365Plugin.DEPENDENCIES))
        self.source.office365 = Mock()

    def test_list_all_returns_every_contact_without_a_filter(self):
        self.source.office365.get_contacts.return_value = (
            [{'id': '1', 'givenName': 'Mario'}, {'id': '2'}],
            2,
        )

        with patch.object(self.source, '_get_microsoft_token', return_value='m'):
            results = self.source.list_all(self.ARGS)

        self.source.office365.get_contacts.assert_called_once_with('m', 'www.bros.com')
        assert_that(
            [r.fields for r in results],
            contains_exactly(
                has_entries(id='1', givenName='Mario'),
                has_entries(id='2', givenName=''),
            ),
        )

    def test_list_all_without_a_microsoft_token_lists_nothing(self):
        for side_effect in (MicrosoftTokenNotFoundException('u'), [None]):
            with patch.object(
                self.source, '_get_microsoft_token', side_effect=side_effect
            ):
                assert_that(self.source.list_all(self.ARGS), equal_to([]))
        self.source.office365.get_contacts.assert_not_called()

    def test_list_all_raises_on_an_unexpected_endpoint(self):
        self.source.office365.get_contacts.side_effect = UnexpectedEndpointException(
            endpoint='www.bros.com', error_code=500
        )

        with patch.object(self.source, '_get_microsoft_token', return_value='m'):
            assert_that(
                calling(self.source.list_all).with_args(self.ARGS),
                raises(SourceListError),
            )
