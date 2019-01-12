# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from flask import request

from wazo_dird.auth import required_acl
from wazo_dird.rest_api import AuthResource


class PhonebookMover(AuthResource):

    def __init__(self, service):
        self._service = service

    @required_acl('dird.phonebook_move_tenant')
    def post(self):
        for tenant in request.json:
            self._service.update_tenant_uuid(tenant['name'], tenant['uuid'])
