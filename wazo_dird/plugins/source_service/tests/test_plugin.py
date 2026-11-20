# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest.mock import Mock

from hamcrest import assert_that, equal_to

from ..plugin import _SourceService


class TestGetPlugin(unittest.TestCase):
    def test_get_plugin_is_the_source_the_source_manager_loads(self) -> None:
        source_manager = Mock()
        service = _SourceService(Mock(), source_manager)

        result = service.get_plugin('some-uuid')

        source_manager.get.assert_called_once_with('some-uuid')
        assert_that(result, equal_to(source_manager.get.return_value))
