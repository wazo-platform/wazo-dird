# Copyright 2016-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import BaseViewPlugin

from .http import (
    ContactAll,
    ContactImport,
    ContactOne,
    PhonebookAll,
    PhonebookOne,
)


class PhonebookViewPlugin(BaseViewPlugin):

    phonebook_all_url = '/tenants/<string:tenant>/phonebooks'
    phonebook_one_url = '/tenants/<string:tenant>/phonebooks/<int:phonebook_id>'
    contact_all_url = '/tenants/<string:tenant>/phonebooks/<int:phonebook_id>/contacts'
    contact_one_url = '/tenants/<string:tenant>/phonebooks/<int:phonebook_id>/contacts/<contact_uuid>'
    contact_import_url = '/tenants/<string:tenant>/phonebooks/<int:phonebook_id>/contacts/import'

    def load(self, dependencies=None):
        api = dependencies['api']
        args = (
            dependencies['services'].get('phonebook'),
            dependencies['auth_client'],
        )

        api.add_resource(ContactAll, self.contact_all_url, resource_class_args=args)
        api.add_resource(ContactImport, self.contact_import_url, resource_class_args=args)
        api.add_resource(ContactOne, self.contact_one_url, resource_class_args=args)
        api.add_resource(PhonebookAll, self.phonebook_all_url, resource_class_args=args)
        api.add_resource(PhonebookOne, self.phonebook_one_url, resource_class_args=args)
