# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from wazo_dird.auth import required_acl
from wazo_dird.rest_api import AuthResource


class Backends(AuthResource):

    def __init__(self, service):
        self._service = service

    @required_acl('dird.backends.read')
    def get(self):
        backends = self._service.list_()
        total = self._service.count()
        filtered = total

        return {
            'total': total,
            'filtered': filtered,
            'items': backends,
        }
