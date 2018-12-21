# Copyright 2015-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase

from hamcrest import assert_that, equal_to
from mock import Mock, patch

from ..plugin import PersonalViewPlugin
from ..http import (
    PersonalAll,
    PersonalImport,
    PersonalOne,
)


@patch('wazo_dird.plugins.views.default_json.plugin.api.add_resource')
class TestPersonalView(TestCase):

    def setUp(self):
        self.plugin = PersonalViewPlugin()

    def test_that_load_with_no_personal_service_does_not_add_routes(self, add_resource):
        self.plugin.load({'config': {},
                          'http_namespace': Mock(),
                          'rest_api': Mock(),
                          'services': {}})

        assert_that(add_resource.call_count, equal_to(0))

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
