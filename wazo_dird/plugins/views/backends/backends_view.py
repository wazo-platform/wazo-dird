# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from wazo_dird import BaseViewPlugin
from wazo_dird.auth import required_acl
from wazo_dird.rest_api import api, AuthResource


class BackendsViewPlugin(BaseViewPlugin):

    def load(self, args):
        api.add_resource(
            Backends,
            '/backends',
            resource_class_args=(args['config'],),
        )


class Backends(AuthResource):

    def __init__(self, config):
        self._enabled_backends = list(config['enabled_plugins']['backends'].keys())

    @required_acl('dird.backends.read')
    def get(self):
        backends = [{'name': name} for name in self._enabled_backends]
        total = len(backends)
        filtered = total

        return {
            'total': total,
            'filtered': filtered,
            'items': backends,
        }
