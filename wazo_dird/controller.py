# Copyright 2014-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import sys
import signal

from functools import partial

from xivo_auth_client import Client as AuthClient
from xivo.consul_helpers import ServiceCatalogRegistration
from xivo.token_renewer import TokenRenewer
from . import auth
from . import plugin_manager
from .bus import Bus
from .rest_api import CoreRestApi
from .service_discovery import self_check
from .source_manager import SourceManager

logger = logging.getLogger(__name__)


def _signal_handler(signum, frame):
    sys.exit(0)


class Controller:

    def __init__(self, config):
        self.config = config
        self.rest_api = CoreRestApi(self.config)
        self.bus = Bus(config)
        auth.set_auth_config(self.config['auth'])
        self.auth_client = AuthClient(**self.config['auth'])
        self.token_renewer = TokenRenewer(self.auth_client)
        self.token_renewer.subscribe_to_token_change(self.auth_client.set_token)
        self._service_registration_params = [
            'wazo-dird',
            self.config.get('uuid'),
            self.config.get('consul'),
            self.config.get('service_discovery'),
            self.config.get('bus'),
            partial(self_check, self.config['rest_api']['https']['port']),
        ]
        self._source_manager = SourceManager(
            self.config['enabled_plugins']['backends'],
            self.config,
            self.auth_client,
            self.token_renewer,
        )

    def run(self):
        self.services = plugin_manager.load_services(
            self.config,
            self.config['enabled_plugins']['services'],
            self._source_manager,
            self.bus,
            self,
        )
        plugin_manager.load_views(
            self.config,
            self.config['enabled_plugins']['views'],
            self.services,
            self.auth_client,
        )
        self._source_manager.set_source_service(self.services['source'])

        signal.signal(signal.SIGTERM, _signal_handler)
        with self.token_renewer:
            with ServiceCatalogRegistration(*self._service_registration_params):
                self.bus.start()
                try:
                    self.rest_api.run()
                finally:
                    plugin_manager.unload_services()
                    self._source_manager.unload_sources()
                    self.bus.stop()
