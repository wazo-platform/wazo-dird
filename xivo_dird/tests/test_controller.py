# -*- coding: utf-8 -*-

# Copyright (C) 2014 Avencall
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


from mock import patch, sentinel as s
from unittest import TestCase

from xivo_dird.controller import Controller


class TestController(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch('xivo_dird.controller.CoreRestApi')
    @patch('xivo.wsgi.run')
    def test_run_starts_rest_api(self, wsgi_run, rest_api_init):
        rest_api = rest_api_init.return_value
        controller = Controller()
        controller.config = {
            'wsgi_socket': s.socket,
            'debug': s.debug,
        }
        controller.run()

        wsgi_run.assert_called_once_with(rest_api.app,
                                         bindAddress=s.socket,
                                         multithreaded=True,
                                         multiprocess=False,
                                         debug=s.debug)

    @patch('xivo_dird.controller.CoreRestApi')
    @patch('xivo_dird.core.plugin_manager.load_services')
    def test_init_loads_plugins(self, load_services, rest_api_init):
        rest_api = rest_api_init.return_value

        Controller()

        load_services.assert_called_once_with({}, rest_api)
