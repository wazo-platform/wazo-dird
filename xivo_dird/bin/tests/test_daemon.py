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

from hamcrest import assert_that, equal_to
from mock import patch, sentinel as s
from unittest import TestCase

from xivo_dird.bin import daemon


@patch('xivo_dird.bin.daemon.pidfile_context')
@patch('xivo_dird.bin.daemon.change_user')
@patch('xivo_dird.bin.daemon.setup_logging')
@patch('xivo_dird.bin.daemon.Controller')
@patch('xivo_dird.bin.daemon.load_config')
class TestXivoDird(TestCase):

    def test_main_injects_argv_into_config_loading(self, load_config, controller_init, setup_logging, change_user, pidfile_context):
        daemon.main(s.argv)

        load_config.assert_called_once_with(s.argv)

    def test_main_injects_config_in_controller(self, load_config, controller_init, setup_logging, change_user, pidfile_context):
        config = load_config.return_value

        daemon.main(s.argv)

        controller_init.assert_called_once_with(config)

    def test_main_setup_logging(self, load_config, controller_init, setup_logging, change_user, pidfile_context):
        load_config.return_value = {
            'log_filename': s.log_filename,
            'foreground': s.foreground,
            'user': s.user,
            'pid_filename': s.pid_filename,
        }

        daemon.main(s.argv)

        setup_logging.assert_called_once_with(s.log_filename, s.foreground)

    def test_main_when_config_user_then_change_user(self, load_config, controller_init, setup_logging, change_user, pidfile_context):
        load_config.return_value = {
            'log_filename': s.log_filename,
            'foreground': s.foreground,
            'user': s.user,
            'pid_filename': s.pid_filename,
        }

        daemon.main(s.argv)

        change_user.assert_called_once_with(s.user)

    def test_main_when_no_config_user_then_dont_change_user(self, load_config, controller_init, setup_logging, change_user, pidfile_context):
        load_config.return_value = {
            'log_filename': s.log_filename,
            'foreground': s.foreground,
            'user': None,
            'pid_filename': s.pid_filename,
        }

        daemon.main(s.argv)

        assert_that(change_user.call_count, equal_to(0))

    def test_main_calls_controller_run(self, load_config, controller_init, setup_logging, change_user, pidfile_context):
        controller = controller_init.return_value
        load_config.return_value = {
            'log_filename': s.log_filename,
            'foreground': s.foreground,
            'user': None,
            'pid_filename': s.pid_filename,
        }

        daemon.main(s.argv)

        controller.run.assert_called_once_with()
