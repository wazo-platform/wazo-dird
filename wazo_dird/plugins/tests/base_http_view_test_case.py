# Copyright (C) 2014 Avencall
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from hamcrest import is_in


class BaseHTTPViewTestCase(unittest.TestCase):

    def is_route_of_app(self, http_app):
        return is_in(self._list_routes(http_app))

    def _list_routes(self, http_app):
        return (rule.rule for rule in http_app.url_map.iter_rules())
