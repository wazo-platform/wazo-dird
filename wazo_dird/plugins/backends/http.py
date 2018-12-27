# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from flask import request

from xivo.mallow_helpers import ListSchema

from wazo_dird.auth import required_acl
from wazo_dird.rest_api import AuthResource


class Backends(AuthResource):

    def __init__(self, service):
        self._service = service

    @required_acl('dird.backends.read')
    def get(self):
        list_params, errors = ListSchema().load(request.args)
        backends = self._service.list_(**list_params)
        total = self._service.count()
        filtered = self._service.count(**list_params)

        return {
            'total': total,
            'filtered': filtered,
            'items': backends,
        }
