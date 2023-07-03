# Copyright 2016-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import BaseViewPlugin

from .http import (
    PhonebookContactAll,
    PhonebookContactImport,
    PhonebookContactOne,
    PhonebookAll,
    PhonebookOne,
)


class PhonebookViewPlugin(BaseViewPlugin):
    def load(self, dependencies=None):
        api = dependencies['api']
        args = (dependencies['services'].get('phonebook'),)

        api.add_resource(
            PhonebookContactAll,
            '/phonebooks/<uuid:phonebook_uuid>/contacts',
            resource_class_args=args,
        )
        api.add_resource(
            PhonebookContactImport,
            '/phonebooks/<uuid:phonebook_uuid>/contacts/import',
            resource_class_args=args,
        )
        api.add_resource(
            PhonebookContactOne,
            '/phonebooks/<uuid:phonebook_uuid>/contacts/<contact_uuid>',
            resource_class_args=args,
        )
        api.add_resource(
            PhonebookAll,
            '/phonebooks',
            resource_class_args=args,
        )
        api.add_resource(
            PhonebookOne,
            '/phonebooks/<uuid:phonebook_uuid>',
            resource_class_args=args,
        )
