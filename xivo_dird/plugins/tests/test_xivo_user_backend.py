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

import unittest

from ..xivo_user_plugin import XivoUserPlugin


class TestXivoUserBackend(unittest.TestCase):

    def setUp(self):
        self._source = XivoUserPlugin()

    def test_that_the_xivo_host_is_used(self):
        config = {
            'host': 'https://xivo.example.com',
            'port': '9487',
        }

        self._source.load({'config': config})
