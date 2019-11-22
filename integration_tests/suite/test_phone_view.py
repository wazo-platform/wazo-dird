# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from .helpers.base import BaseDirdIntegrationTest
from .helpers.config import new_phone_view_config
from .helpers.constants import VALID_TOKEN_MAIN_TENANT, VALID_UUID

from hamcrest import assert_that, contains_string, equal_to, matches_regexp, not_

URL_REGEX = '.*<URL>.*{}.*</URL>.*'
TAG_REGEX = '.*<{tag}>.*'


class TestPhoneView(BaseDirdIntegrationTest):

    asset = 'phone_view'
    profile = 'default'
    config_factory = new_phone_view_config

    def test_given_invalid_offset_then_lookup_return_400(self):
        result = self.get_lookup_cisco_result(
            self.profile, VALID_UUID, term='A', token=VALID_TOKEN_MAIN_TENANT, offset=-1
        )
        assert_that(result.status_code, equal_to((400)))

    def test_given_invalid_limit_then_lookup_return_400(self):
        result = self.get_lookup_cisco_result(
            self.profile, VALID_UUID, term='A', token=VALID_TOKEN_MAIN_TENANT, limit=-1
        )
        assert_that(result.status_code, equal_to((400)))

    def test_that_dird_replace_url_by_proxy(self):
        proxy_url = 'http://my-proxy.com/input'
        result = self.get_menu_cisco(self.profile, VALID_UUID, proxy=proxy_url)

        assert_that(result, matches_regexp(URL_REGEX.format(proxy_url)))

    def test_that_menu_return_input_url_when_no_proxy(self):
        result = self.get_menu_cisco(
            self.profile, VALID_UUID, token=VALID_TOKEN_MAIN_TENANT
        )

        assert_that(result, matches_regexp(URL_REGEX.format('/input')))
        assert_that(result, not_(matches_regexp(URL_REGEX.format('/menu'))))

    def test_that_menu_return_input_url_when_profile_name_menu(self):
        profile = 'menu'
        result = self.get_menu_cisco(profile, VALID_UUID, token=VALID_TOKEN_MAIN_TENANT)

        assert_that(result, matches_regexp(URL_REGEX.format('/input/menu')))

    def test_that_input_replace_url_by_proxy(self):
        proxy_url = 'http://my-proxy.com/lookup'
        result = self.get_input_cisco(self.profile, VALID_UUID, proxy=proxy_url)

        assert_that(result, matches_regexp(URL_REGEX.format(proxy_url)))

    def test_that_input_return_lookup_url_when_no_proxy(self):
        result = self.get_input_cisco(
            self.profile, VALID_UUID, token=VALID_TOKEN_MAIN_TENANT
        )

        assert_that(result, matches_regexp(URL_REGEX.format('/lookup')))
        assert_that(result, not_(matches_regexp(URL_REGEX.format('/input'))))

    def test_that_input_return_lookup_url_when_profile_name_input(self):
        profile = 'input'
        result = self.get_input_cisco(
            profile, VALID_UUID, token=VALID_TOKEN_MAIN_TENANT
        )

        assert_that(result, matches_regexp(URL_REGEX.format('/lookup/input')))

    def test_that_lookup_replace_url_by_proxy_when_paging(self):
        proxy_url = 'http://my-proxy.com/lookup'
        result = self.get_lookup_cisco(
            self.profile, VALID_UUID, term='user', proxy=proxy_url
        )

        assert_that(result, matches_regexp(URL_REGEX.format(proxy_url)))

    def test_that_lookup_return_lookup_url_when_no_proxy_and_paging(self):
        result = self.get_lookup_cisco(self.profile, VALID_UUID, term='user')

        assert_that(result, matches_regexp(URL_REGEX.format('/lookup')))

    def test_that_lookup_return_lookup_template(self):
        result = self.get_lookup_cisco(self.profile, VALID_UUID, term='toto')

        assert_that(
            result, matches_regexp(TAG_REGEX.format(tag='CiscoIPPhoneDirectory'))
        )

    def test_that_lookup_return_result(self):
        result = self.get_lookup_cisco(self.profile, VALID_UUID, term='Alice')

        assert_that(result, contains_string('Alice'))
        assert_that(result, contains_string('5555555555'))

    def test_that_lookup_return_400_when_no_term(self):
        result = self.get_lookup_cisco_result(
            self.profile, VALID_UUID, token=VALID_TOKEN_MAIN_TENANT
        )

        assert_that(result.status_code, equal_to(400))

    def test_that_lookup_return_404_when_unknown_profile(self):
        result = self.get_lookup_cisco_result(
            'quiproquo', VALID_UUID, term='alice', token=VALID_TOKEN_MAIN_TENANT
        )

        assert_that(result.status_code, equal_to(404))

    def test_cisco_input_route(self):
        result = self.get_input_cisco_result(
            self.profile, VALID_UUID, token=VALID_TOKEN_MAIN_TENANT
        )
        assert_that(result.status_code, equal_to((200)))

    def test_cisco_menu_route(self):
        result = self.get_menu_cisco_result(
            self.profile, VALID_UUID, token=VALID_TOKEN_MAIN_TENANT
        )
        assert_that(result.status_code, equal_to((200)))

    def test_cisco_lookup_route(self):
        result = self.get_lookup_cisco_result(
            self.profile, VALID_UUID, term='Alice', token=VALID_TOKEN_MAIN_TENANT
        )
        assert_that(result.status_code, equal_to((200)))

    def test_thomson_lookup_route(self):
        result = self.get_lookup_thomson_result(
            self.profile, VALID_UUID, term='Alice', token=VALID_TOKEN_MAIN_TENANT
        )
        assert_that(result.status_code, equal_to((200)))

    def test_htek_lookup_route(self):
        result = self.get_lookup_htek_result(
            self.profile, VALID_UUID, term='Alice', token=VALID_TOKEN_MAIN_TENANT
        )
        assert_that(result.status_code, equal_to((200)))
