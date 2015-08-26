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
from hamcrest import matches_regexp
from hamcrest import not_

URL_REGEX = '.*<URL>.*{}.*</URL>.*'
TAG_REGEX = '.*<{tag}>.*'


class TestCiscoView(BaseDirdIntegrationTest):

    asset = 'cisco_view'
    profile = 'default'

    def test_that_dird_replace_url_by_proxy(self):
        proxy_url = 'http://my-proxy.com/lookup'
        result = self.get_menu_cisco(proxy=proxy_url)

        assert_that(result, matches_regexp(URL_REGEX.format(proxy_url)))

    def test_that_menu_return_lookup_url_when_no_proxy(self):
        result = self.get_menu_cisco(token=VALID_TOKEN)

        assert_that(result, matches_regexp(URL_REGEX.format('/lookup')))
        assert_that(result, not_(matches_regexp(URL_REGEX.format('/menu'))))

    def test_that_lookup_replace_url_by_proxy(self):
        proxy_url = 'http://my-proxy.com/lookup'
        result = self.get_lookup_cisco(profile=self.profile, proxy=proxy_url)

        assert_that(result, matches_regexp(URL_REGEX.format(proxy_url)))

    def test_that_lookup_return_lookup_url_when_no_proxy(self):
        result = self.get_lookup_cisco(profile=self.profile)

        assert_that(result, matches_regexp(URL_REGEX.format('/lookup')))

    def test_that_lookup_return_special_template_when_no_term(self):
        result = self.get_lookup_cisco(profile=self.profile)

        assert_that(result, matches_regexp(TAG_REGEX.format(tag='CiscoIPPhoneInput')))

    def test_that_lookup_return_lookup_template(self):
        result = self.get_lookup_cisco(profile=self.profile, term='toto')

        assert_that(result, matches_regexp(TAG_REGEX.format(tag='CiscoIPPhoneDirectory')))
