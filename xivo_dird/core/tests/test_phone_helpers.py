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

from hamcrest import assert_that
from hamcrest import equal_to
from unittest import TestCase
from xivo_dird.core.phone_helpers import PhoneDisplay


class TestPhoneDisplay(TestCase):

    def setUp(self):
        self.display_name = 'display1'
        self.profile_name = 'profile1'

    def test_get_fields(self):
        displays = {
            self.display_name: {
                'name': 'foo',
                'number': 'bar',
            }
        }
        profile_to_display = {
            self.profile_name: self.display_name,
        }
        phone_display = PhoneDisplay(displays, profile_to_display)

        name_field = phone_display.get_name_field(self.profile_name)
        number_field = phone_display.get_number_field(self.profile_name)

        assert_that(name_field, equal_to('foo'))
        assert_that(number_field, equal_to('bar'))

    def test_get_fields_no_display_with_default_display(self):
        displays = {
            PhoneDisplay.DEFAULT_DISPLAY_NAME: {
                'name': 'foo',
                'number': 'bar',
            }
        }
        profile_to_display = {
            self.profile_name: self.display_name,
        }
        phone_display = PhoneDisplay(displays, profile_to_display)

        name_field = phone_display.get_name_field(self.profile_name)
        number_field = phone_display.get_number_field(self.profile_name)

        assert_that(name_field, equal_to('foo'))
        assert_that(number_field, equal_to('bar'))

    def test_get_fields_no_profile_to_display_with_default_display(self):
        displays = {
            PhoneDisplay.DEFAULT_DISPLAY_NAME: {
                'name': 'foo',
                'number': 'bar',
            }
        }
        phone_display = PhoneDisplay(displays, {})

        name_field = phone_display.get_name_field(self.profile_name)
        number_field = phone_display.get_number_field(self.profile_name)

        assert_that(name_field, equal_to('foo'))
        assert_that(number_field, equal_to('bar'))

    def test_new_from_config(self):
        views_config = {
            'displays_phone': {}
        }

        phone_display = PhoneDisplay.new_from_config(views_config)

        assert_that(phone_display._displays, equal_to({}))
        assert_that(phone_display._profile_to_display, equal_to({}))
