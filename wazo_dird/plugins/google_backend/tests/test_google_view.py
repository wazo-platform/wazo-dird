# Copyright 2019-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from unittest.mock import Mock, ANY

from ..http import GoogleList, GoogleItem
from ..plugin import GoogleViewPlugin


class TestGoogleView(TestCase):
    def setUp(self):
        self.plugin = GoogleViewPlugin()
        self.api = Mock()

    def test_when_load_then_routes_added(self):
        dependencies = {
            'config': {'auth': Mock()},
            'http_namespace': Mock(),
            'api': self.api,
            'services': {'source': Mock()},
        }

        self.plugin.load(dependencies)

        self.api.add_resource.assert_any_call(GoogleList, ANY, resource_class_args=ANY)
        self.api.add_resource.assert_any_call(GoogleItem, ANY, resource_class_args=ANY)
