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

from hamcrest import assert_that, equal_to
from unittest import TestCase
from mock import patch

from xivo_dird.plugins import phone_view


class TestPhoneView(TestCase):

    @patch('xivo_dird.plugins.phone_view.request')
    def test_that_build_next_url_return_input_url_when_is_menu(self, MockedRequest):
        url = 'http://127.0.0.1:9489/0.1/directories/{}/profile/vendor'
        expected_result = url.format('input')
        MockedRequest.base_url = url.format('menu')
        result = phone_view._build_next_url('menu')

        assert_that(result, equal_to(expected_result))

    @patch('xivo_dird.plugins.phone_view.request')
    def test_that_build_next_url_return_input_url_when_is_menu_with_profile_menu(self, MockedRequest):
        url = 'http://127.0.0.1:9489/0.1/directories/{}/menu/vendor'
        expected_result = url.format('input')
        MockedRequest.base_url = url.format('menu')
        result = phone_view._build_next_url('menu')

        assert_that(result, equal_to(expected_result))

    @patch('xivo_dird.plugins.phone_view.request')
    def test_that_build_next_url_return_lookup_url_when_is_input(self, MockedRequest):
        url = 'http://127.0.0.1:9489/0.1/directories/{}/profile/vendor'
        expected_result = url.format('lookup')
        MockedRequest.base_url = url.format('input')
        result = phone_view._build_next_url('input')

        assert_that(result, equal_to(expected_result))

    @patch('xivo_dird.plugins.phone_view.request')
    def test_that_build_next_url_return_lookup_url_when_is_input_with_profile_input(self, MockedRequest):
        url = 'http://127.0.0.1:9489/0.1/directories/{}/input/vendor'
        expected_result = url.format('lookup')
        MockedRequest.base_url = url.format('input')
        result = phone_view._build_next_url('input')

        assert_that(result, equal_to(expected_result))

    @patch('xivo_dird.plugins.phone_view.request')
    def test_that_build_next_url_return_same_url_when_is_lookup(self, MockedRequest):
        url = 'http://127.0.0.1:9489/0.1/directories/lookup/profile/vendor'
        expected_result = url
        MockedRequest.base_url = url
        result = phone_view._build_next_url('lookup')

        assert_that(result, equal_to(expected_result))
