# Copyright 2016-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import BaseViewPlugin

from .http import ContactAll, ContactImport, ContactOne, PhonebookAll, PhonebookOne


class PhonebookViewPlugin(BaseViewPlugin):
    def load(self, dependencies=None):
        api = dependencies['api']
        args = (dependencies['services'].get('phonebook'), dependencies['auth_client'])

        api.add_resource(
            ContactAll,
            '/tenants/<string:tenant>/phonebooks/<int:phonebook_id>/contacts',
            resource_class_args=args,
        )
        api.add_resource(
            ContactImport,
            '/tenants/<string:tenant>/phonebooks/<int:phonebook_id>/contacts/import',
            resource_class_args=args,
        )
        api.add_resource(
            ContactOne,
            '/tenants/<string:tenant>/phonebooks/<int:phonebook_id>/contacts/<contact_uuid>',
            resource_class_args=args,
        )
        api.add_resource(
            PhonebookAll,
            '/tenants/<string:tenant>/phonebooks',
            resource_class_args=args,
        )
        api.add_resource(
            PhonebookOne,
            '/tenants/<string:tenant>/phonebooks/<int:phonebook_id>',
            resource_class_args=args,
        )
