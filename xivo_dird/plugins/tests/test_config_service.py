# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Proformatique, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import unittest

from hamcrest import assert_that, equal_to
from mock import sentinel as s

from ..config_service import Service


class TestConfigService(unittest.TestCase):

    def test_that_get_current_config_returns_the_config(self):
        service = Service(s.original_config)

        config = service.get_current_config()

        assert_that(config, equal_to(s.original_config))
