# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from wazo_dird import BaseViewPlugin
from wazo_dird.rest_api import api

from . import http


# This plugin is used for the tenant uuid migration between wazo-auth and dird
class PhonebookTenantMoverPlugin(BaseViewPlugin):

    def load(self, dependencies):
        phonebook_service = dependencies['services'].get('phonebook')
        api.add_resource(
            http.PhonebookMover,
            '/phonebook_move_tenant',
            resource_class_args=(phonebook_service,),
        )
