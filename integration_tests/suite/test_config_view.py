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

from hamcrest import assert_that, equal_to

from .base_dird_integration_test import BaseDirdIntegrationTest, VALID_TOKEN


class TestConfigView(BaseDirdIntegrationTest):

    asset = 'config-view'

    def test_get_config(self):
        result = self.get_config(token=VALID_TOKEN)

        # Expected
        # {'foo': {'bar': 'main',
        #          'baz': 'conf.d'
        #          'other': 'overwritten'}}
        assert_that(result['foo']['bar'], equal_to('main'))
        assert_that(result['foo']['baz'], equal_to('conf.d'))
        assert_that(result['foo']['other'], equal_to('overwritten'))
