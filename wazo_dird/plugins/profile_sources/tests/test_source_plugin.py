# Copyright 2019-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from unittest.mock import Mock

from hamcrest import assert_that, calling, not_, raises

from ..plugin import SourceViewPlugin


class TestSourcePlugin(TestCase):

    DEPENDENCIES = {'api': Mock(), 'services': {'profile': Mock()}}

    def setUp(self):
        self.source = SourceViewPlugin()

    def test_load(self):
        self.source.load(self.DEPENDENCIES)
        assert_that(
            calling(self.source.load).with_args(self.DEPENDENCIES),
            not_(raises(Exception)),
        )
