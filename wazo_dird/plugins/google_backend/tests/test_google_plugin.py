# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from typing import cast
from unittest import TestCase
from unittest.mock import Mock, patch

from hamcrest import assert_that, calling, equal_to, not_, raises

from wazo_dird.plugins.base_plugins import SourcePluginDependencies

from ..plugin import GooglePlugin


class TestGooglePlugin(TestCase):
    DEPENDENCIES = {
        'main_config': {},
        'config': {
            'auth': {'host': '9497'},
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
            not_(raises(Exception)),
        )

    def test_first_match_predicate(self):
        self.source.load(cast(SourcePluginDependencies, self.DEPENDENCIES))

        term = '5555551234'

        mario = {'name': 'Mario Bros', 'numbers': {}}
        luigi = {
            'name': 'Luigi Bros',
            'numbers_by_label': {'mobile': '5555551234'},
            'numbers': ['5555551234'],
        }
        peach = {
            'name': 'Peach',
            'numbers_by_label': {'mobile': '5555551234', 'business': '4185553212'},
            'numbers': ['5555551234', '4185553212'],
        }

        assert_that(self.source._first_match_predicate(term, mario), equal_to(False))
        assert_that(self.source._first_match_predicate(term, luigi), equal_to(True))
        assert_that(self.source._first_match_predicate(term, peach), equal_to(True))
        assert_that(
            self.source._first_match_predicate(term[:-1], peach), equal_to(False)
        )

    def test_match_all_keeps_the_last_matching_contact_per_term(self):
        self.source.load(cast(SourcePluginDependencies, self.DEPENDENCIES))
        mario = {'id': '1', 'name': 'Mario', 'numbers': ['111']}
        luigi = {'id': '2', 'name': 'Luigi', 'numbers': ['222']}
        other_luigi = {'id': '3', 'name': 'Other Luigi', 'numbers': ['222']}
        self.source.google = Mock(
            get_all_contacts=Mock(return_value=[mario, luigi, other_luigi])
        )

        with patch.object(self.source, '_get_google_token', return_value='token'):
            results = self.source.match_all(['111', '222', '333'])

        assert_that(
            {term: result.fields['id'] for term, result in results.items()},
            equal_to({'111': '1', '222': '3'}),
        )
