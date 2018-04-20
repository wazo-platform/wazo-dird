# -*- coding: utf-8 -*-
# Copyright (C) 2016 Proformatique, Inc.
# SPDX-License-Identifier: GPL-3.0+

import unittest

from hamcrest import assert_that, equal_to
from mock import sentinel as s

from ..config_service import Service


class TestConfigService(unittest.TestCase):

    def test_that_get_current_config_returns_the_config(self):
        service = Service(s.original_config)

        config = service.get_current_config()

        assert_that(config, equal_to(s.original_config))
