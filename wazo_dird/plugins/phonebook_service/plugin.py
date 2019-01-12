# Copyright 2016-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from marshmallow import fields, Schema, validate, pre_load
from unidecode import unidecode

from wazo_dird import BaseServicePlugin
from wazo_dird import database
from wazo_dird.exception import (
    InvalidContactException,
    InvalidPhonebookException,
)

logger = logging.getLogger(__name__)


class _PhonebookSchema(Schema):
    name = fields.String(validate=validate.Length(min=1, max=255), required=True)
    description = fields.String(allow_none=True)

    @pre_load
    def ensure_dict(self, data):
        return data or {}


class PhonebookServicePlugin(BaseServicePlugin):

    def load(self, args):
        self._config = args.get('config')
        if not self._config:
            msg = '{} should be loaded with "config" but received: {}'.format(
                self.__class__.__name__,
                ','.join(args.keys()),
            )
            raise ValueError(msg)

        self._db_uri = self._config.get('db_uri')
        if not self._db_uri:
            msg = '{} requires a "db_uri" in its configuration'.format(self.__class__.__name__)
            raise ValueError(msg)

        Session = self._new_db_session(self._db_uri)
        return _PhonebookService(
            database.PhonebookCRUD(Session),
            database.PhonebookContactCRUD(Session),
            database.TenantCRUD(Session),
        )

    def _new_db_session(self, db_uri):
        self._Session = scoped_session(sessionmaker())
        engine = create_engine(db_uri)
        self._Session.configure(bind=engine)
        return self._Session


class _PhonebookService:

    def __init__(self, phonebook_crud, contact_crud, tenant_crud):
        self._phonebook_crud = phonebook_crud
        self._contact_crud = contact_crud
        self._tenant_crud = tenant_crud

    def list_contact(self, tenant_uuid, phonebook_id, limit=None, offset=None,
                     order=None, direction=None, **params):
        results = self._contact_crud.list(tenant_uuid, phonebook_id, **params)
        if order:
            reverse = direction == 'desc'
            results = sorted(results, key=lambda x: unidecode(x.get(order, '')), reverse=reverse)
        if offset:
            results = results[offset:]
        if limit:
            results = results[:limit]
        return results

    def list_phonebook(self, tenant_uuid, **params):
        return self._phonebook_crud.list(tenant_uuid, **params)

    def count_contact(self, tenant_uuid, phonebook_id, **params):
        return self._contact_crud.count(tenant_uuid, phonebook_id, **params)

    def count_phonebook(self, tenant_uuid, **params):
        return self._phonebook_crud.count(tenant_uuid, **params)

    def create_contact(self, tenant_uuid, phonebook_id, contact_info):
        validated_contact = self._validate_contact(contact_info)
        return self._contact_crud.create(tenant_uuid, phonebook_id, validated_contact)

    def create_phonebook(self, tenant_uuid, phonebook_info):
        body, errors = _PhonebookSchema().load(phonebook_info)
        if errors:
            raise InvalidPhonebookException(errors)
        return self._phonebook_crud.create(tenant_uuid, body)

    def edit_contact(self, tenant_uuid, phonebook_id, contact_uuid, contact_info):
        return self._contact_crud.edit(
            tenant_uuid,
            phonebook_id,
            contact_uuid,
            self._validate_contact(contact_info),
        )

    def edit_phonebook(self, tenant_uuid, phonebook_id, phonebook_info):
        body, errors = _PhonebookSchema().load(phonebook_info)
        if errors:
            raise InvalidPhonebookException(errors)
        return self._phonebook_crud.edit(tenant_uuid, phonebook_id, body)

    def delete_contact(self, tenant_uuid, phonebook_id, contact_uuid):
        return self._contact_crud.delete(tenant_uuid, phonebook_id, contact_uuid)

    def delete_phonebook(self, tenant_uuid, phonebook_id):
        return self._phonebook_crud.delete(tenant_uuid, phonebook_id)

    def get_contact(self, tenant_uuid, phonebook_id, contact_uuid):
        return self._contact_crud.get(tenant_uuid, phonebook_id, contact_uuid)

    def get_phonebook(self, tenant_uuid, phonebook_id):
        return self._phonebook_crud.get(tenant_uuid, phonebook_id)

    def import_contacts(self, tenant_uuid, phonebook_id, contacts):
        to_add, errors = [], []
        for contact in contacts:
            try:
                to_add.append(self._validate_contact(contact))
            except InvalidContactException:
                errors.append(contact)

        created, failed = self._contact_crud.create_many(tenant_uuid, phonebook_id, to_add)

        return created, failed + errors

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
        logger.info('done')

    @staticmethod
    def _validate_contact(body):
        if not body:
            raise InvalidContactException('Contacts cannot be empty')
        if '' in body:
            raise InvalidContactException('Contacts cannot have empty keys')
        if None in body:
            raise InvalidContactException('Contacts cannot have null keys')
        body.pop('id', None)
        return body
