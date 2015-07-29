# -*- coding: utf-8 -*-
# Copyright (C) 2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

from .base_dird_integration_test import BaseDirdIntegrationTest

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import equal_to
from hamcrest import has_entry
from hamcrest import has_key
from hamcrest import not_


class TestListPersonal(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_listing_empty_personal_returns_empty_list(self):
        result = self.get_personal()

        assert_that(result['items'], contains())


class TestAddPersonal(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_created_personal_are_listed(self):
        self.post_personal({'firstname': 'Alice'})
        self.post_personal({'firstname': 'Bob'})

        result = self.get_personal()

        assert_that(result['items'], contains_inanyorder(
            has_entry('firstname', 'Alice'),
            has_entry('firstname', 'Bob')))


class TestAddPersonalNonAscii(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_created_personal_are_listed(self):
        self.post_personal({'firstname': 'Àlîce'})

        raw = self.get_personal()
        formatted = self.get_personal_with_profile('default')

        assert_that(raw['items'], contains_inanyorder(
            has_entry('firstname', u'Àlîce')))
        assert_that(formatted['results'], contains_inanyorder(
            has_entry('column_values', contains(u'Àlîce', None, None, False))))


class TestRemovePersonal(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_removed_personal_are_not_listed(self):
        self.post_personal({'firstname': 'Alice'})
        bob = self.post_personal({'firstname': 'Bob'})
        self.post_personal({'firstname': 'Charlie'})
        self.delete_personal(bob['id'])

        result = self.get_personal()

        assert_that(result['items'], contains_inanyorder(
            has_entry('firstname', 'Alice'),
            has_entry('firstname', 'Charlie')))


class TestPersonalId(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_created_personal_has_an_id(self):
        alice = self.post_personal({'firstname': 'Alice'}, token='valid-token')
        bob = self.post_personal({'firstname': 'Bob'}, token='valid-token')

        assert_that(alice['id'], not_(equal_to(bob['id'])))


class TestPersonalPersistence(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_personal_are_saved_across_dird_restart(self):
        self.post_personal({})

        result_before = self.get_personal()

        assert_that(result_before['items'], contains(has_key('id')))

        self._run_cmd('docker-compose kill dird')
        self._run_cmd('docker-compose rm -f dird')
        self._run_cmd('docker-compose run --rm sync')

        result_after = self.get_personal()

        assert_that(result_after['items'], contains(has_key('id')))
        assert_that(result_before['items'][0]['id'], equal_to(result_after['items'][0]['id']))


class TestPersonalVisibility(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_personal_are_only_visible_for_the_same_token(self):
        self.post_personal({'firstname': 'Alice'}, token='valid-token-1')
        self.post_personal({'firstname': 'Bob'}, token='valid-token-1')
        self.post_personal({'firstname': 'Charlie'}, token='valid-token-2')

        result_1 = self.get_personal(token='valid-token-1')
        result_2 = self.get_personal(token='valid-token-2')

        assert_that(result_1['items'], contains_inanyorder(has_entry('firstname', 'Alice'),
                                                           has_entry('firstname', 'Bob')))
        assert_that(result_2['items'], contains(has_entry('firstname', 'Charlie')))


class TestPersonalListWithProfileEmpty(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_listing_personal_with_profile_empty_returns_empty_list(self):
        result = self.get_personal_with_profile('default')

        assert_that(result['results'], contains())


class TestPersonalListWithProfile(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_listing_personal_with_profile(self):
        self.post_personal({'firstname': 'Alice'})
        self.post_personal({'firstname': 'Bob'})

        result = self.get_personal_with_profile('default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', None, None, False)),
            has_entry('column_values', contains('Bob', None, None, False))))


class TestLookupPersonal(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_lookup_includes_personal_contacts(self):
        self.post_personal({'firstname': 'Alice'})
        self.post_personal({'firstname': 'Bob'})

        result = self.lookup('ali', 'default')

        import pprint
        pprint.pprint(result)
        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', None, None, False))))


class TestLookupPersonalNonAscii(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_lookup_accepts_non_ascii_in_term(self):
        self.post_personal({'firstname': 'Céline'})

        result = self.lookup(u'Céline', 'default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains(u'Céline', None, None, False))))


class TestLookupPersonalFuzzyAsciiMatch1(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_lookup_matches_non_ascii_with_ascii(self):
        self.post_personal({'firstname': 'Céline'})

        result = self.lookup(u'celine', 'default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains(u'Céline', None, None, False))))


class TestLookupPersonalFuzzyAsciiMatch2(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_lookup_matches_non_ascii_with_ascii(self):
        self.post_personal({'firstname': 'Etienne'})

        result = self.lookup(u'étienne', 'default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains(u'Etienne', None, None, False))))

# TODO
# update contact
# validation upon contact creation/update
# consul unreachable
# invalid profile
# other errors
