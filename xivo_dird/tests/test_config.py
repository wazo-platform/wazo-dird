# -*- coding: utf-8 -*-
# Copyright (C) 2014-2016 Avencall
# SPDX-License-Identifier: GPL-3.0+

import logging

from hamcrest import assert_that, has_entries, equal_to
from mock import Mock, patch, sentinel as s
from unittest import TestCase

from xivo_dird import config


@patch('__builtin__.print', Mock())
@patch('xivo_dird.config.open', create=True)
class TestConfig(TestCase):

    def test_load_when_no_args_and_no_default_config_file_then_return_default_values(self, mock_open):
        mock_open.side_effect = IOError('no such file')
        config._DEFAULT_CONFIG = {
            'config': 'default',
            'config_file': '/etc/xivo-dird/config.yml',
            'extra_config_files': '/etc/xivo-dird/conf.d/',
        }

        result = config.load(s.logger, [])

        assert_that(result, has_entries(config._DEFAULT_CONFIG))

    def test_load_when_config_file_in_argv_then_read_config_from_file(self, _):
        result = config.load(s.logger, ['-c', 'my_file'])

        assert_that(result['config_file'], equal_to('my_file'))

    def test_load_when_foreground_in_argv_then_ignore_default_value(self, mock_open):
        mock_open.side_effect = IOError('no such file')

        result = config.load(s.logger, ['-f'])

        assert_that(result['foreground'], equal_to(True))

    def test_load_when_user_in_argv_then_ignore_default_value(self, mock_open):
        mock_open.side_effect = IOError('no such file')

        result = config.load(s.logger, ['-u', 'my_user'])

        assert_that(result['user'], equal_to('my_user'))

    def test_load_when_debug_in_argv_then_ignore_default_value(self, mock_open):
        mock_open.side_effect = IOError('no such file')

        result = config.load(s.logger, ['-d'])

        assert_that(result['debug'], equal_to(True))

    def test_load_when_log_level_in_argv_then_ignore_default_value(self, mock_open):
        mock_open.side_effect = IOError('no such file')

        result = config.load(s.logger, ['-l', 'ERROR'])

        assert_that(result['log_level'], equal_to(logging.ERROR))

    def test_multiple_profile_type_number_return_true(self, _):
        profile = [
            {'title': 'Number', 'type': 'number'},
            {'title': 'Mobile', 'type': 'number'},
        ]
        result = config._multiple_profile_type_number(profile)

        assert_that(result, equal_to(True))

    def test_multiple_profile_type_number_return_false(self, _):
        profile = [
            {'title': 'Number', 'type': 'number'},
        ]
        result = config._multiple_profile_type_number(profile)

        assert_that(result, equal_to(False))
