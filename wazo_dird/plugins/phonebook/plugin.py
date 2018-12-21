# Copyright 2016-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from wazo_dird import BaseViewPlugin
from wazo_dird.rest_api import api

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

    def load(self, args=None):
        phonebook_service = args['services'].get('phonebook')
        if phonebook_service:
            ContactAll.configure(phonebook_service)
            ContactImport.configure(phonebook_service)
            ContactOne.configure(phonebook_service)
            PhonebookAll.configure(phonebook_service)
            PhonebookOne.configure(phonebook_service)
            api.add_resource(ContactAll, self.contact_all_url)
            api.add_resource(ContactImport, self.contact_import_url)
            api.add_resource(ContactOne, self.contact_one_url)
            api.add_resource(PhonebookAll, self.phonebook_all_url)
            api.add_resource(PhonebookOne, self.phonebook_one_url)
