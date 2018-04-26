# -*- coding: utf-8 -*-
# Copyright 2013-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo_dird.plugins.base_plugins import BaseServicePlugin
from xivo_dird.plugins.base_plugins import BaseViewPlugin
from xivo_dird.plugins.base_plugins import BaseSourcePlugin
from xivo_dird.plugins.source_result import make_result_class

__all__ = [
    'BaseServicePlugin',
    'BaseViewPlugin',
    'BaseSourcePlugin',
    'make_result_class',
]
