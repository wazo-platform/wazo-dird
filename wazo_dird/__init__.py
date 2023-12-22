# Copyright 2013-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import sys

# Compatibility for old plugins < 22.03
from wazo_dird import http_server
from wazo_dird.plugins.base_plugins import (
    BaseServicePlugin,
    BaseSourcePlugin,
    BaseViewPlugin,
)
from wazo_dird.plugins.source_result import make_result_class

sys.modules['wazo_dird.rest_api'] = sys.modules['wazo_dird.http_server']

__all__ = [
    'BaseServicePlugin',
    'BaseViewPlugin',
    'BaseSourcePlugin',
    'http_server',
    'make_result_class',
]
