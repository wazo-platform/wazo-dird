# Copyright 2019-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird.auth import required_acl
from wazo_dird.http import AuthResource


class StatusResource(AuthResource):
    def __init__(self, status_aggregator, config):
        self.status_aggregator = status_aggregator
        self._config = config

    @required_acl('dird.status.read')
    def get(self):
        result = {
            'bus_consumer': {
                'status': self.status_aggregator.status()['bus_consumer']['status']
            },
            'rest_api': {
                'status': self.status_aggregator.status()['rest_api']['status']
            },
            'master_tenant': {
                'status': 'ok'
                if self._config['auth'].get('master_tenant_uuid')
                else 'fail'
            },
        }
        return result, 200
