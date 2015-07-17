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


class TestAddPrivate(BaseDirdIntegrationTest):

    asset = 'privates_only'

    def test_that_created_privates_are_listed(self):
        self.post_private({'firstname': 'Alice'})
        self.post_private({'firstname': 'Bob'})

        result = self.get_privates()

        assert_that(result['items'], contains_inanyorder(
            has_entry('firstname', 'Alice'),
            has_entry('firstname', 'Bob')))


class TestRemovePrivate(BaseDirdIntegrationTest):

    asset = 'privates_only'

    def test_that_removed_privates_are_not_listed(self):
        self.post_private({'firstname': 'Alice'})
        bob = self.post_private({'firstname': 'Bob'})
        self.post_private({'firstname': 'Charlie'})
        self.delete_private(bob['id'])

        result = self.get_privates()

        assert_that(result['items'], contains_inanyorder(
            has_entry('firstname', 'Alice'),
            has_entry('firstname', 'Charlie')))


class TestPrivateId(BaseDirdIntegrationTest):

    asset = 'privates_only'

    def test_that_created_private_has_an_id(self):
        alice = self.post_private({'firstname': 'Alice'}, token='valid-token')
        bob = self.post_private({'firstname': 'Bob'}, token='valid-token')

        assert_that(alice['id'], not_(equal_to(bob['id'])))


class TestPrivatesPersistence(BaseDirdIntegrationTest):

    asset = 'privates_only'

    def test_that_privates_are_saved_across_dird_restart(self):
        self.post_private({})

        result_before = self.get_privates()

        assert_that(result_before['items'], contains(has_key('id')))

        self._run_cmd('docker-compose kill dird')
        self._run_cmd('docker-compose rm -f dird')
        self._run_cmd('docker-compose run --rm sync')

        result_after = self.get_privates()

        assert_that(result_after['items'], contains(has_key('id')))
        assert_that(result_before['items'][0]['id'], equal_to(result_after['items'][0]['id']))


class TestPrivatesVisibility(BaseDirdIntegrationTest):

    asset = 'privates_only'

    def test_that_favorites_are_only_visible_for_the_same_token(self):
        self.post_private({'firstname': 'Alice'}, token='valid-token-1')
        self.post_private({'firstname': 'Bob'}, token='valid-token-1')
        self.post_private({'firstname': 'Charlie'}, token='valid-token-2')

        result_1 = self.get_privates(token='valid-token-1')
        result_2 = self.get_privates(token='valid-token-2')

        assert_that(result_1['items'], contains_inanyorder(has_entry('firstname', 'Alice'),
                                                           has_entry('firstname', 'Bob')))
        assert_that(result_2['items'], contains(has_entry('firstname', 'Charlie')))

# TODO
# list with profile
# update contact
# lookup = return privates
# favorite privates
# validation upon contact creation/update
# other errors
