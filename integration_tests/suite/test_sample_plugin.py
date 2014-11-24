# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Avencall
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

from .base_dird_integration_test import BaseDirdIntegrationTest
from hamcrest import assert_that
from hamcrest import contains


class TestSamplePlugin(BaseDirdIntegrationTest):

    asset = 'sample_backend'

    def test_that_john_doe_is_returned(self):
        result = self.lookup('lol', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains('John', 'Doe', 'It works but this xivo-dird installation is still using the default configuration'))
