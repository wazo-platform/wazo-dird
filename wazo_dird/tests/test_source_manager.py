# Copyright 2014-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from typing import cast
from unittest.mock import Mock
from unittest.mock import sentinel as s

from wazo_dird.config import Config
from wazo_dird.source_manager import SourceManager


class TestSourceManager(unittest.TestCase):
    def test_unload_sources(self):
        source_1 = Mock()
        source_2 = Mock()

        manager = SourceManager(
            {}, cast(Config, {'sources': {}}), s.auth_client, s.token_renewer
        )
        manager._sources = {'s1': source_1, 's2': source_2}

        manager.unload_sources()

        source_1.unload.assert_called_once_with()
        source_2.unload.assert_called_once_with()

    def test_invalidate_drops_the_source_and_tells_the_subscribers(self):
        manager = SourceManager(
            {}, cast(Config, {'sources': {}}), s.auth_client, s.token_renewer
        )
        manager._sources = {'s1': Mock()}
        evict = Mock()
        manager.subscribe_invalidate(evict)

        manager.invalidate('s1')
        manager.invalidate('never-loaded')

        self.assertNotIn('s1', manager._sources)
        self.assertEqual(evict.call_args_list, [(('s1',),), (('never-loaded',),)])
