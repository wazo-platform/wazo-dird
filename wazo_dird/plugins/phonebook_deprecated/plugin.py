# Copyright 2016-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from wazo_dird import BaseViewPlugin

from .http import (
    DeprecatedPhonebookAll,
    DeprecatedPhonebookContactAll,
    DeprecatedPhonebookContactImport,
    DeprecatedPhonebookContactOne,
    DeprecatedPhonebookOne,
)

logger = logging.getLogger(__name__)


class DeprecatedPhonebookViewPlugin(BaseViewPlugin):
    def load(self, dependencies=None):
        api = dependencies['api']
        args = (dependencies['services'].get('phonebook'), dependencies['auth_client'])

        logger.warning(
            "Loading deprecated phonebook view plugin. Expect plugin to be removed in a future version."
        )

        api.add_resource(
            DeprecatedPhonebookContactAll,
            '/tenants/<string:tenant>/phonebooks/<int:phonebook_id>/contacts',
            resource_class_args=args,
        )
        api.add_resource(
            DeprecatedPhonebookContactImport,
            '/tenants/<string:tenant>/phonebooks/<int:phonebook_id>/contacts/import',
            resource_class_args=args,
        )
        api.add_resource(
            DeprecatedPhonebookContactOne,
            '/tenants/<string:tenant>/phonebooks/<int:phonebook_id>/contacts/<contact_uuid>',
            resource_class_args=args,
        )
        api.add_resource(
            DeprecatedPhonebookAll,
            '/tenants/<string:tenant>/phonebooks',
            resource_class_args=args,
        )
        api.add_resource(
            DeprecatedPhonebookOne,
            '/tenants/<string:tenant>/phonebooks/<int:phonebook_id>',
            resource_class_args=args,
        )
