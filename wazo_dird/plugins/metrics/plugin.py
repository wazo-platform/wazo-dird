# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.flask.metrics import init_flask_metrics

from wazo_dird import BaseViewPlugin
from wazo_dird.plugin_manager import ViewDependencies


class MetricsViewPlugin(BaseViewPlugin):
    def load(self, dependencies: ViewDependencies) -> None:
        init_flask_metrics(dependencies['flask_app'], dependencies['api'])
