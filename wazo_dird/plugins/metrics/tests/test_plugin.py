# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import cast
from unittest.mock import patch
from unittest.mock import sentinel as s

from wazo_dird.plugin_manager import ViewDependencies

from ..plugin import MetricsViewPlugin


@patch('wazo_dird.plugins.metrics.plugin.init_flask_metrics')
def test_load_instruments_the_app(init_flask_metrics):
    dependencies = cast(ViewDependencies, {'flask_app': s.flask_app, 'api': s.api})

    MetricsViewPlugin().load(dependencies)

    init_flask_metrics.assert_called_once_with(s.flask_app, s.api)
