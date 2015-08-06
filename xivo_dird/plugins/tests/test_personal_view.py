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

from unittest import TestCase

from hamcrest import assert_that
from hamcrest import equal_to
from mock import Mock
from mock import patch

from xivo_dird.plugins.personal_view import PersonalAll
from xivo_dird.plugins.personal_view import PersonalImport
from xivo_dird.plugins.personal_view import PersonalOne
from xivo_dird.plugins.personal_view import PersonalViewPlugin


class TestPersonalView(TestCase):

    def setUp(self):
        self.plugin = PersonalViewPlugin()

    @patch('xivo_dird.plugins.default_json_view.api.add_resource')
    def test_that_load_with_no_personal_service_does_not_add_routes(self, add_resource):
        self.plugin.load({'config': {},
                          'http_namespace': Mock(),
                          'rest_api': Mock(),
                          'services': {}})

        assert_that(add_resource.call_count, equal_to(0))

    @patch('xivo_dird.plugins.default_json_view.api.add_resource')
    def test_that_load_adds_the_routes(self, add_resource):
        args = {
            'config': {'displays': {},
                       'profile_to_display': {}},
            'http_namespace': Mock(),
            'rest_api': Mock(),
            'services': {'personal': Mock()},
        }

        self.plugin.load(args)

        add_resource.assert_any_call(PersonalAll, PersonalViewPlugin.personal_all_url)
        add_resource.assert_any_call(PersonalOne, PersonalViewPlugin.personal_one_url)
        add_resource.assert_any_call(PersonalImport, PersonalViewPlugin.personal_import_url)
