# Copyright 2018-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from flask import request

from wazo_dird.auth import required_acl
from wazo_dird.http import LegacyAuthResource

from .schemas import ListSchema


class Backends(LegacyAuthResource):
    def __init__(self, service):
        self._service = service

    @required_acl('dird.backends.read')
    def get(self):
        list_params = ListSchema().load(request.args)

        backends = self._service.list_(**list_params)
        filtered = self._service.count(**list_params)
        total = self._service.count()

        return {'total': total, 'filtered': filtered, 'items': backends}
