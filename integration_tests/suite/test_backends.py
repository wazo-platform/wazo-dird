# Copyright 2018-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, contains, contains_inanyorder, has_entries

from .helpers.base import BaseDirdIntegrationTest


class TestBackends(BaseDirdIntegrationTest):
    asset = 'all_routes'

    def test_list(self):
        result = self.client.backends.list()
        # not sample which is disabled
        # not unknown which is not installed
        expected = [
            'conference',
            'csv',
            'csv_ws',
            'google',
            'ldap',
            'office365',
            'personal',
            'phonebook',
            'wazo',
        ]
        self._assert_matches(result, 9, 9, contains_inanyorder, *expected)

        result = self.client.backends.list(search='a')
        self._assert_matches(
            result, 9, 3, contains_inanyorder, 'ldap', 'personal', 'wazo'
        )

        result = self.client.backends.list(name='csv')
        self._assert_matches(result, 9, 1, contains, 'csv')

        result = self.client.backends.list(order='name', direction='asc')
        expected = [
            'conference',
            'csv',
            'csv_ws',
            'google',
            'ldap',
            'office365',
            'personal',
            'phonebook',
            'wazo',
        ]
        self._assert_matches(result, 9, 9, contains, *expected)

        result = self.client.backends.list(order='name', direction='desc')
        expected = [
            'wazo',
            'phonebook',
            'personal',
            'office365',
            'ldap',
            'google',
            'csv_ws',
            'csv',
            'conference',
        ]
        self._assert_matches(result, 9, 9, contains, *expected)

        result = self.client.backends.list(limit=2, offset=5)
        self._assert_matches(result, 9, 9, contains, 'office365', 'personal')

        result = self.client.backends.list(limit=2)
        self._assert_matches(result, 9, 9, contains, 'conference', 'csv')

        result = self.client.backends.list(offset=7)
        self._assert_matches(result, 9, 9, contains, 'phonebook', 'wazo')

    @staticmethod
    def _assert_matches(result, total, filtered, matcher, *names):
        assert_that(
            result,
            has_entries(
                total=total,
                filtered=filtered,
                items=matcher(*[has_entries(name=name) for name in names]),
            ),
        )
