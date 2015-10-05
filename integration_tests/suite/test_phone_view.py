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
from .base_dird_integration_test import VALID_TOKEN

from hamcrest import assert_that
from hamcrest import contains_string
from hamcrest import equal_to
from hamcrest import matches_regexp
from hamcrest import not_

URL_REGEX = '.*<URL>.*{}.*</URL>.*'
TAG_REGEX = '.*<{tag}>.*'


class TestPhoneView(BaseDirdIntegrationTest):

    asset = 'phone_view'
    profile = 'default'

    def test_given_invalid_offset_then_lookup_return_400(self):
        result = self.get_lookup_cisco_result(term='A', profile=self.profile, token=VALID_TOKEN, offset=-1)
        assert_that(result.status_code, equal_to((400)))

    def test_given_invalid_limit_then_lookup_return_400(self):
        result = self.get_lookup_cisco_result(term='A', profile=self.profile, token=VALID_TOKEN, limit=-1)
        assert_that(result.status_code, equal_to((400)))

    def test_that_dird_replace_url_by_proxy(self):
        proxy_url = 'http://my-proxy.com/input'
        result = self.get_menu_cisco(profile=self.profile, proxy=proxy_url)

        assert_that(result, matches_regexp(URL_REGEX.format(proxy_url)))

    def test_that_menu_return_input_url_when_no_proxy(self):
        result = self.get_menu_cisco(profile=self.profile, token=VALID_TOKEN)

        assert_that(result, matches_regexp(URL_REGEX.format('/input')))
        assert_that(result, not_(matches_regexp(URL_REGEX.format('/menu'))))

    def test_that_menu_return_input_url_when_profile_name_menu(self):
        profile = 'menu'
        result = self.get_menu_cisco(profile=profile, token=VALID_TOKEN)

        assert_that(result, matches_regexp(URL_REGEX.format('/input/menu')))

    def test_that_input_replace_url_by_proxy(self):
        proxy_url = 'http://my-proxy.com/lookup'
        result = self.get_input_cisco(profile=self.profile, proxy=proxy_url)

        assert_that(result, matches_regexp(URL_REGEX.format(proxy_url)))

    def test_that_input_return_lookup_url_when_no_proxy(self):
        result = self.get_input_cisco(profile=self.profile, token=VALID_TOKEN)

        assert_that(result, matches_regexp(URL_REGEX.format('/lookup')))
        assert_that(result, not_(matches_regexp(URL_REGEX.format('/input'))))

    def test_that_input_return_lookup_url_when_profile_name_input(self):
        profile = 'input'
        result = self.get_input_cisco(profile=profile, token=VALID_TOKEN)

        assert_that(result, matches_regexp(URL_REGEX.format('/lookup/input')))

    def test_that_lookup_replace_url_by_proxy_when_paging(self):
        proxy_url = 'http://my-proxy.com/lookup'
        result = self.get_lookup_cisco(profile=self.profile, term='user', proxy=proxy_url)

        assert_that(result, matches_regexp(URL_REGEX.format(proxy_url)))

    def test_that_lookup_return_lookup_url_when_no_proxy_and_paging(self):
        result = self.get_lookup_cisco(profile=self.profile, term='user')

        assert_that(result, matches_regexp(URL_REGEX.format('/lookup')))

    def test_that_lookup_return_lookup_template(self):
        result = self.get_lookup_cisco(profile=self.profile, term='toto')

        assert_that(result, matches_regexp(TAG_REGEX.format(tag='CiscoIPPhoneDirectory')))

    def test_that_lookup_return_result(self):
        result = self.get_lookup_cisco(profile=self.profile, term='Alice')

        assert_that(result, contains_string('Alice'))
        assert_that(result, contains_string('5555555555'))

    def test_that_lookup_return_400_when_no_term(self):
        result = self.get_lookup_cisco_result(profile=self.profile, token=VALID_TOKEN)

        assert_that(result.status_code, equal_to(400))
