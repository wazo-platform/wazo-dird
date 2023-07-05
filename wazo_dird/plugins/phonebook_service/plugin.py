# Copyright 2016-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
import logging

from marshmallow import ValidationError, fields, Schema, validate, pre_load
from unidecode import unidecode

from wazo_dird import BaseServicePlugin
from wazo_dird import database
from wazo_dird.database.helpers import Session
from wazo_dird.database.queries.phonebook import Direction, PhonebookKey
from wazo_dird.exception import InvalidContactException, InvalidPhonebookException

logger = logging.getLogger(__name__)


class _PhonebookSchema(Schema):
    name = fields.String(validate=validate.Length(min=1, max=255), required=True)
    description = fields.String(allow_none=True)

    @pre_load
    def ensure_dict(self, data, **kwargs):
        return data or {}


class PhonebookServicePlugin(BaseServicePlugin):
    def load(self, args):
        self._config = args.get('config')
        if not self._config:
            msg = '{} should be loaded with "config" but received: {}'.format(
                self.__class__.__name__, ','.join(args.keys())
            )
            raise ValueError(msg)

        return _PhonebookService(
            database.PhonebookCRUD(Session),
            database.PhonebookContactCRUD(Session),
        )


class _PhonebookService:
    def __init__(self, phonebook_crud, contact_crud):
        self._phonebook_crud: database.PhonebookCRUD = phonebook_crud
        self._contact_crud: database.PhonebookContactCRUD = contact_crud

    def list_contact(
        self,
        tenant_uuid: str,
        phonebook_key: PhonebookKey,
        limit: int | None = None,
        offset: int | None = None,
        order: str | None = None,
        direction: Direction | None = None,
        **params,
    ):
        results = self._contact_crud.list(
            tenant_uuid,
            phonebook_key,
            **params,
        )
        if order:
            reverse = direction == 'desc'
            results = sorted(
                results,
                key=lambda x: unidecode(str(x.get(order, ''))),
                reverse=reverse,  # type: ignore[typeddict-item]
            )
        if offset:
            results = results[offset:]
        if limit:
            results = results[:limit]
        return results

    def list_phonebook(self, tenant_uuid: str, **params):
        return self._phonebook_crud.list(
            tenant_uuid,
            **params,
        )

    def count_contact(self, tenant_uuid: str, phonebook_key: PhonebookKey, **params):
        return self._contact_crud.count(tenant_uuid, phonebook_key, **params)

    def count_phonebook(self, tenant_uuid: str, **params):
        return self._phonebook_crud.count(tenant_uuid, **params)

    def create_contact(
        self, tenant_uuid: str, phonebook_key: PhonebookKey, contact_info: dict
    ):
        validated_contact = self._validate_contact(contact_info)
        return self._contact_crud.create(tenant_uuid, phonebook_key, validated_contact)

    def create_phonebook(self, tenant_uuid: str, phonebook_info: dict):
        try:
            body: dict = _PhonebookSchema().load(phonebook_info)  # type: ignore
        except ValidationError as e:
            raise InvalidPhonebookException(e.messages)
        return self._phonebook_crud.create(tenant_uuid, body)

    def edit_contact(
        self,
        tenant_uuid: str,
        phonebook_key: PhonebookKey,
        contact_uuid: str,
        contact_info: dict,
    ):
        return self._contact_crud.edit(
            tenant_uuid,
            phonebook_key,
            contact_uuid,
            self._validate_contact(contact_info),
        )

    def edit_phonebook(
        self, tenant_uuid: str, phonebook_key: PhonebookKey, phonebook_info: dict
    ):
        try:
            body: dict = _PhonebookSchema().load(phonebook_info)  # type: ignore
        except ValidationError as e:
            raise InvalidPhonebookException(e.messages)
        return self._phonebook_crud.edit(tenant_uuid, phonebook_key, body)

    def delete_contact(
        self, tenant_uuid: str, phonebook_key: PhonebookKey, contact_uuid: str
    ):
        return self._contact_crud.delete(tenant_uuid, phonebook_key, contact_uuid)

    def delete_phonebook(self, tenant_uuid: str, phonebook_key: PhonebookKey):
        return self._phonebook_crud.delete(tenant_uuid, phonebook_key)

    def get_contact(
        self, tenant_uuid: str, phonebook_key: PhonebookKey, contact_uuid: str
    ):
        return self._contact_crud.get(tenant_uuid, phonebook_key, contact_uuid)

    def get_phonebook(self, tenant_uuid: str, phonebook_key: PhonebookKey):
        return self._phonebook_crud.get(tenant_uuid, phonebook_key)

    def import_contacts(
        self, tenant_uuid: str, phonebook_key: PhonebookKey, contacts: list[dict]
    ):
        to_add, errors = [], []
        for contact in contacts:
            try:
                to_add.append(self._validate_contact(contact))
            except InvalidContactException:
                errors.append(contact)

        created, failed = self._contact_crud.create_many(
            tenant_uuid, phonebook_key, to_add
        )

        return created, failed + errors

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
