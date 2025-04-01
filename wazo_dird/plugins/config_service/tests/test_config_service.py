# Copyright 2016-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest.mock import Mock
from unittest.mock import sentinel as s

from hamcrest import assert_that, equal_to

from ..plugin import Service


class TestConfigService(unittest.TestCase):
    def test_that_get_config_returns_the_config(self):
        tenant_crud = None
        confd_client = None
        service = Service(
            s.original_config, Mock(), s.controller, tenant_crud, confd_client
        )

        config = service.get_config()

        assert_that(config, equal_to(s.original_config))
