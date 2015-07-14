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
from hamcrest import contains_inanyorder
from hamcrest import has_entry


class TestAddPrivate(BaseDirdIntegrationTest):
    asset = 'privates_only'

    def test_that_created_privates_are_listed(self):
        self.post_private({'firstname': 'Alice'})
        self.post_private({'firstname': 'Bob'})

        result = self.get_privates()

        assert_that(result['items'], contains_inanyorder(
            has_entry('firstname', 'Alice'),
            has_entry('firstname', 'Bob')))

# TODO
# persistence
# list with profile
# deletion
# update contact
# different tokens = different contacts
# lookup = return privates
# favorite privates
# validation upon contact creation/update
# other errors
