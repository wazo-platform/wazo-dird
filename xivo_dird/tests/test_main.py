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

import logging

from mock import Mock
from mock import patch
from unittest import TestCase
from xivo_dird import main


class TestMain(TestCase):

    def test_that_main_inititlize_the_logger(self):
        main._init_logger = Mock()

        main.main()

        main._init_logger.assert_called_once_with()

    def test_that_main_calls_run(self):
        main._run = Mock()

        main.main()

        main._run.assert_called_once_with()


@patch('logging.getLogger')
class TestInitLogger(TestCase):

    def test_that_init_logger_sets_the_level_to_debug(self, get_logger_mock):
        logger = Mock()
        get_logger_mock.return_value = logger

        main._init_logger()

        logger.setLevel.assert_called_once_with(logging.DEBUG)

    @patch('logging.StreamHandler')
    def test_that_a_stream_handler_is_set(self, stream_handler_mock, get_logger_mock):
        handler = Mock()
        logger = Mock()
        get_logger_mock.return_value = logger
        stream_handler_mock.return_value = handler

        main._init_logger()

        logger.addHandler.assert_called_once_with(handler)
