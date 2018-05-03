# -*- coding: utf-8 -*-
# Copyright 2014-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import sys
import signal

from functools import partial

from xivo.consul_helpers import ServiceCatalogRegistration
from . import auth
from . import plugin_manager
from .bus import Bus
from .rest_api import CoreRestApi

from .service_discovery import self_check

logger = logging.getLogger(__name__)


def _signal_handler(signum, frame):
    sys.exit(0)


class Controller(object):

    def __init__(self, config):
        self.config = config
        self.rest_api = CoreRestApi(self.config)
        self.bus = Bus(config)
        auth.set_auth_config(self.config['auth'])
        self._service_registration_params = ['wazo-dird',
                                             self.config.get('uuid'),
                                             self.config.get('consul'),
                                             self.config.get('service_discovery'),
                                             self.config.get('bus'),
                                             partial(self_check,
                                                     self.config['rest_api']['https']['port'])]

    def run(self):
        self.sources = plugin_manager.load_sources(self.config['enabled_plugins']['backends'],
                                                   self.config)
        self.services = plugin_manager.load_services(self.config,
                                                     self.config['enabled_plugins']['services'],
                                                     self.sources,
                                                     self.bus)
        plugin_manager.load_views(self.config['views'],
                                  self.config['enabled_plugins']['views'],
                                  self.services,
                                  self.rest_api)

        signal.signal(signal.SIGTERM, _signal_handler)
        with ServiceCatalogRegistration(*self._service_registration_params):
            self.bus.start()
            try:
                self.rest_api.run()
            finally:
                plugin_manager.unload_services()
                plugin_manager.unload_sources()
                self.bus.stop()
