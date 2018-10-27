# Copyright (C) 2016 Proformatique, Inc.
# SPDX-License-Identifier: GPL-3.0+

from wazo_dird import BaseServicePlugin


class ConfigServicePlugin(BaseServicePlugin):

    def __init__(self):
        self._service = None

    def load(self, args):
        return Service(args['config'])


class Service(object):

    def __init__(self, config):
        self._config = config

    def get_current_config(self):
        return self._config
