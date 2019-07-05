# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase

from hamcrest import assert_that, equal_to
from mock import patch

from .. import http


@patch('wazo_dird.plugins.phone.http.request')
class TestPhoneView(TestCase):

    def test_that_build_next_url_return_input_url_when_is_menu(self, MockedRequest):
        url = 'http://127.0.0.1:9489/0.1/directories/{}/profile/vendor'
        expected_result = url.format('input')
        MockedRequest.base_url = url.format('menu')
        result = http._build_next_url('menu')

        assert_that(result, equal_to(expected_result))

    def test_that_build_next_url_return_input_url_when_is_menu_with_profile_menu(
            self, MockedRequest,
    ):
        url = 'http://127.0.0.1:9489/0.1/directories/{}/menu/vendor'
        expected_result = url.format('input')
        MockedRequest.base_url = url.format('menu')
        result = http._build_next_url('menu')

        assert_that(result, equal_to(expected_result))

    def test_that_build_next_url_return_lookup_url_when_is_input(self, MockedRequest):
        url = 'http://127.0.0.1:9489/0.1/directories/{}/profile/vendor'
        expected_result = url.format('lookup')
        MockedRequest.base_url = url.format('input')
        result = http._build_next_url('input')

        assert_that(result, equal_to(expected_result))

    def test_that_build_next_url_return_lookup_url_when_is_input_with_profile_input(
            self, MockedRequest,
    ):
        url = 'http://127.0.0.1:9489/0.1/directories/{}/input/vendor'
        expected_result = url.format('lookup')
        MockedRequest.base_url = url.format('input')
        result = http._build_next_url('input')

        assert_that(result, equal_to(expected_result))

    def test_that_build_next_url_return_same_url_when_is_lookup(self, MockedRequest):
        url = 'http://127.0.0.1:9489/0.1/directories/lookup/profile/vendor'
        expected_result = url
        MockedRequest.base_url = url
        result = http._build_next_url('lookup')

        assert_that(result, equal_to(expected_result))
