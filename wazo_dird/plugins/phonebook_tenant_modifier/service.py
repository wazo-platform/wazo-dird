# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from wazo_dird import database
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

logger = logging.getLogger(__name__)


class PhonebookMoverService:

    def __init__(self, db_uri):
        Session = scoped_session(sessionmaker())
        engine = create_engine(db_uri)
        Session.configure(bind=engine)
        self._tenant_crud = database.TenantCRUD(Session)
        self._phonebook_crud = database.PhonebookCRUD(Session)

    def update_tenant_uuid(self, tenant_name, tenant_uuid):
        logger.info('updating tenant uuid: %s -> %s', tenant_name, tenant_uuid)
        tenants = self._tenant_crud.list_(name=tenant_name)
        logger.info('matching tenants: %s', tenants)
        for tenant in tenants:
            old_uuid = tenant['uuid']
            phonebooks = self._phonebook_crud.list(old_uuid)
            logger.info('updating %s phonebooks', len(phonebooks))
            for phonebook in phonebooks:
                self._phonebook_crud.update_tenant(old_uuid, phonebook['id'], tenant_uuid)
            logger.info('deleting tenant: %s', old_uuid)
            self._tenant_crud.delete(old_uuid)
        logger.info('done')
