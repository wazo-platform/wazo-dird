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
