# -*- coding: utf-8 -*-
# Copyright 2014-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import (
    assert_that,
    equal_to,
)
from mock import (
    ANY,
    patch,
    sentinel as s,
)
from unittest import TestCase

from ..main import main


@patch('xivo_dird.main.set_xivo_uuid')
@patch('xivo_dird.main.pidfile_context')
@patch('xivo_dird.main.change_user')
@patch('xivo_dird.main.xivo_logging')
@patch('xivo_dird.main.Controller')
@patch('xivo_dird.main.load_config')
class TestXivoDird(TestCase):

    def test_main_injects_argv_into_config_loading(self, load_config, *_):
        main(s.argv)

        load_config.assert_called_once_with(ANY, s.argv)

    def test_main_injects_config_in_controller(self, load_config, controller_init, *_):
        config = load_config.return_value

        main(s.argv)

        controller_init.assert_called_once_with(config)

    def test_main_setup_logging(self, load_config, _, xivo_logging, *__):
        load_config.return_value = {
            'debug': s.debug,
            'log_filename': s.log_filename,
            'log_level': s.log_level,
            'foreground': s.foreground,
            'user': s.user,
            'pid_filename': s.pid_filename,
        }

        main(s.argv)

        xivo_logging.setup_logging.assert_called_once_with(s.log_filename, s.foreground, s.debug, s.log_level)

    def test_main_when_config_user_then_change_user(self, load_config, _, __, change_user, *___):
        load_config.return_value = {
            'debug': s.debug,
            'log_filename': s.log_filename,
            'log_level': s.log_level,
            'foreground': s.foreground,
            'user': s.user,
            'pid_filename': s.pid_filename,
        }

        main(s.argv)

        change_user.assert_called_once_with(s.user)

    def test_main_when_no_config_user_then_dont_change_user(self, load_config, _, __, change_user, *___):
        load_config.return_value = {
            'debug': s.debug,
            'log_filename': s.log_filename,
            'log_level': s.log_level,
            'foreground': s.foreground,
            'user': None,
            'pid_filename': s.pid_filename,
        }

        main(s.argv)

        assert_that(change_user.call_count, equal_to(0))

    def test_main_calls_controller_run(self, load_config, controller_init, *_):
        controller = controller_init.return_value
        load_config.return_value = {
            'debug': s.debug,
            'log_filename': s.log_filename,
            'log_level': s.log_level,
            'foreground': s.foreground,
            'user': None,
            'pid_filename': s.pid_filename,
        }

        main(s.argv)

        controller.run.assert_called_once_with()
