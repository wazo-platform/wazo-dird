# Copyright 2016-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import BaseServicePlugin


class ConfigServicePlugin(BaseServicePlugin):

    def __init__(self):
        self._service = None

    def load(self, args):
        return Service(args['config'])


class Service:

    def __init__(self, config):
        self._config = config

    def get_current_config(self):
        return self._config
