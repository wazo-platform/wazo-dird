# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from wazo_dird import BaseViewPlugin
from wazo_dird.rest_api import api

from . import (
    http,
    service,
)


# This plugin is used for the tenant uuid migration between wazo-auth and dird
class PhonebookTenantMoverPlugin(BaseViewPlugin):

    def load(self, dependencies):
        db_uri = dependencies['config']['db_uri']
        tenant_mover_service = service.PhonebookMoverService(db_uri)
        api.add_resource(
            http.PhonebookMover,
            '/phonebook_move_tenant',
            resource_class_args=(tenant_mover_service,),
        )
