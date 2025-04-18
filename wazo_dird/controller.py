# Copyright 2014-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import signal
import threading
from functools import partial

from wazo_auth_client import Client as AuthClient
from wazo_confd_client import Client as ConfdClient
from xivo.consul_helpers import ServiceCatalogRegistration
from xivo.status import StatusAggregator
from xivo.token_renewer import TokenRenewer

from . import auth, plugin_manager
from .bus import CoreBus
from .config import Config
from .database.helpers import init_db
from .http_server import CoreRestApi
from .service_discovery import self_check
from .source_manager import SourceManager

logger = logging.getLogger(__name__)


class Controller:
    config: Config
    rest_api: CoreRestApi
    bus: CoreBus
    auth_client: AuthClient
    token_renewer: TokenRenewer
    status_aggregator: StatusAggregator

    def __init__(self, config: Config):
        self.config = config
        self._stopping_thread: threading.Thread | None = None
        init_db(config['db_uri'], pool_size=config['rest_api']['max_threads'])
        self.rest_api = CoreRestApi(self.config)
        self.bus = CoreBus(config.get('uuid'), **config['bus'])
        auth.set_auth_config(self.config['auth'])
        self.auth_client = AuthClient(**self.config['auth'])
        self.confd_client = ConfdClient(**self.config['confd'])
        self.token_renewer = TokenRenewer(self.auth_client)
        if not self.config['auth'].get('master_tenant_uuid'):
            self.token_renewer.subscribe_to_next_token_details_change(
                auth.init_master_tenant
            )
        self.token_renewer.subscribe_to_token_change(self.auth_client.set_token)
        self.token_renewer.subscribe_to_token_change(self.confd_client.set_token)
        self.status_aggregator = StatusAggregator()
        self.status_aggregator.add_provider(auth.provide_status)
        self._service_registration_params = [
            'wazo-dird',
            self.config.get('uuid'),
            self.config.get('consul'),
            self.config.get('service_discovery'),
            self.config.get('bus'),
            partial(self_check, self.config['rest_api']['port']),
        ]
        self._source_manager = SourceManager(
            self.config['enabled_plugins']['backends'],
            self.config,
            self.auth_client,
            self.token_renewer,
        )

    def run(self):
        signal.signal(signal.SIGTERM, partial(_signal_handler, self))
        signal.signal(signal.SIGINT, partial(_signal_handler, self))
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
            self.status_aggregator,
            self.rest_api,
        )
        self._source_manager.set_source_service(self.services['source'])
        self.status_aggregator.add_provider(self.bus.provide_status)

        with self.token_renewer:
            with self.bus:
                with ServiceCatalogRegistration(*self._service_registration_params):
                    try:
                        self.rest_api.run()
                    finally:
                        plugin_manager.unload_views()
                        plugin_manager.unload_services()
                        self._source_manager.unload_sources()
                        if self._stopping_thread:
                            self._stopping_thread.join()

    def stop(self, reason):
        logger.warning('Stopping wazo-dird: %s', reason)
        self._stopping_thread = threading.Thread(target=self.rest_api.stop, name=reason)
        self._stopping_thread.start()


def _signal_handler(controller, signum, frame):
    controller.stop(reason=signal.Signals(signum).name)
