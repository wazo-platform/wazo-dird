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

import flask
import unittest

from hamcrest import assert_that
from hamcrest import is_in
from xivo_dird.plugins.default_json_view.default_json_view import JsonViewPlugin


class TestJsonViewPlugin(unittest.TestCase):

    def setUp(self):
        self.http_app = flask.Flask(__name__)

    def test_default_view_load_no_args(self):
        p = JsonViewPlugin()

        p.load()

    def test_that_load_adds_the_route(self):
        args = {
            'http_app': self.http_app,
        }

        p = JsonViewPlugin()
        p.load(args)

        route = '/{version}/directories/lookup/<profile>'.format(version=JsonViewPlugin.API_VERSION)
        self.assert_has_route(self.http_app, route)

    def assert_has_route(self, http_app, route):
        routes = self._list_routes(http_app)
        assert_that(route, is_in(routes))

    def _list_routes(self, http_app):
        routes = []
        for rule in http_app.url_map.iter_rules():
            routes.append(rule.rule)
        return routes
