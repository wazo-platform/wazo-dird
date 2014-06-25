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

from mock import patch
from unittest import TestCase
from xivo_dird import main


class TestMain(TestCase):

    def setUp(self):
        self.argparse_patch = patch('argparse.ArgumentParser')
        self.daemon_patch = patch('xivo.daemonize.daemonize')
        self.daemon_lock_patch = patch('xivo.daemonize.lock_pidfile_or_die')
        self.daemon_unlock_patch = patch('xivo.daemonize.unlock_pidfile')
        self.log_patch = patch('xivo_dird.main.setup_logging')
        self.wsgi_patch = patch('xivo_dird.main.WSGIServer')

        self.argparse = self.argparse_patch.start()
        self.daemonize = self.daemon_patch.start()
        self.daemon_lock = self.daemon_lock_patch.start()
        self.daemon_unlock = self.daemon_unlock_patch.start()
        self.log = self.log_patch.start()
        self.wsgi = self.wsgi_patch.start()

        self.args = self.argparse.return_value.parse_args.return_value
        self.args.foreground = False

    def tearDown(self):
        self.argparse_patch.stop()
        self.daemon_patch.stop()
        self.daemon_lock_patch.stop()
        self.daemon_unlock_patch.stop()
        self.log_patch.stop()
        self.wsgi_patch.stop()

    def test_that_main_initialize_the_logger(self):
        main.main()

        self.log.assert_called_once_with(main._LOG_FILENAME, self.args.foreground, self.args.debug)

    def test_that_dird_is_daemonized(self):
        main.main()

        self.daemonize.assert_called_once_with()

    def test_that_dird_has_a_pid_file(self):
        main.main()

        self.daemon_lock.assert_called_once_with(main._PID_FILENAME)
        self.daemon_unlock.asssert_called_once_with(main._PID_FILENAME)

    def test_that_the_pid_file_is_unlocked_on_exception(self):
        self.wsgi.run.side_effect = AssertionError('Unexpected')

        main.main()

        self.daemon_lock.assert_called_once_with(main._PID_FILENAME)
        self.daemon_unlock.assert_called_once_with(main._PID_FILENAME)
