# Copyright 2016-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from typing import Any, cast

from marshmallow import Schema, ValidationError, fields, pre_load, validate

from wazo_dird import BaseServicePlugin, database
from wazo_dird.database.helpers import Session
from wazo_dird.database.queries.base import ContactInfo, Direction
from wazo_dird.database.queries.phonebook import (
    ContactEntryError,
    PhonebookDict,
    PhonebookKey,
)
from wazo_dird.exception import InvalidContactException, InvalidPhonebookException
from wazo_dird.plugin_helpers.sorting import sort_contacts
from wazo_dird.plugin_manager import ServiceDependencies

logger = logging.getLogger(__name__)


class _PhonebookSchema(Schema):  # type: ignore[misc]
    name = fields.String(validate=validate.Length(min=1, max=255), required=True)
    description = fields.String(allow_none=True)

    @pre_load  # type: ignore[untyped-decorator]
    def ensure_dict(self, data: dict[str, Any] | None, **kwargs: Any) -> dict[str, Any]:
        return data or {}


class PhonebookServicePlugin(BaseServicePlugin):
    def load(self, args: ServiceDependencies) -> _PhonebookService:
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
    def __init__(
        self,
        phonebook_crud: database.PhonebookCRUD,
        contact_crud: database.PhonebookContactCRUD,
    ):
        self._phonebook_crud: database.PhonebookCRUD = phonebook_crud
        self._contact_crud: database.PhonebookContactCRUD = contact_crud

    def list_contacts(
        self,
        visible_tenants: list[str],
        phonebook_key: PhonebookKey,
        limit: int | None = None,
        offset: int | None = None,
        order: str | None = None,
        direction: Direction | None = None,
        order_insensitive: bool = False,
        **params: Any,
    ) -> list[ContactInfo]:
        results = self._contact_crud.list(
            visible_tenants,
            phonebook_key,
            **params,
        )
        sorted_results = cast(
            list[ContactInfo],
            sort_contacts(
                cast('list[dict[str, Any]]', results),
                order=order,
                direction=direction,
                order_insensitive=order_insensitive,
            ),
        )
        start = offset or 0
        return sorted_results[start : start + limit if limit else None]

    def list_phonebook(
        self, visible_tenants: list[str], **params: Any
    ) -> list[PhonebookDict]:
        return self._phonebook_crud.list(
            visible_tenants,
            order=params.get('order'),
            direction=params.get('direction'),
            limit=params.get('limit'),
            offset=params.get('offset'),
            search=params.get('search'),
        )

    def count_contact(
        self, visible_tenants: list[str], phonebook_key: PhonebookKey, **params: Any
    ) -> int:
        return self._contact_crud.count(visible_tenants, phonebook_key, **params)

    def count_phonebook(self, visible_tenants: list[str], **params: Any) -> int:
        return self._phonebook_crud.count(visible_tenants, **params)

    def create_contact(
        self,
        visible_tenants: list[str],
        phonebook_key: PhonebookKey,
        contact_info: dict[str, Any],
    ) -> ContactInfo:
        validated_contact = self._validate_contact(contact_info)
        return self._contact_crud.create(
            visible_tenants, phonebook_key, validated_contact
        )

    def create_phonebook(
        self, tenant_uuid: str, phonebook_info: dict[str, Any]
    ) -> PhonebookDict:
        try:
            body: dict[str, Any] = _PhonebookSchema().load(phonebook_info)
        except ValidationError as e:
            raise InvalidPhonebookException(e.messages)
        return self._phonebook_crud.create(tenant_uuid, body)

    def edit_contact(
        self,
        visible_tenants: list[str],
        phonebook_key: PhonebookKey,
        contact_uuid: str,
        contact_info: dict[str, Any],
    ) -> ContactInfo:
        return self._contact_crud.edit(
            visible_tenants,
            phonebook_key,
            contact_uuid,
            self._validate_contact(contact_info),
        )

    def edit_phonebook(
        self,
        visible_tenants: list[str],
        phonebook_key: PhonebookKey,
        phonebook_info: dict[str, Any],
    ) -> PhonebookDict:
        try:
            body: dict[str, Any] = _PhonebookSchema().load(phonebook_info)
        except ValidationError as e:
            raise InvalidPhonebookException(e.messages)
        return self._phonebook_crud.edit(visible_tenants, phonebook_key, body)

    def delete_contact(
        self, visible_tenants: list[str], phonebook_key: PhonebookKey, contact_uuid: str
    ) -> None:
        return self._contact_crud.delete(visible_tenants, phonebook_key, contact_uuid)

    def delete_phonebook(
        self, visible_tenants: list[str], phonebook_key: PhonebookKey
    ) -> None:
        self._phonebook_crud.delete(visible_tenants, phonebook_key)

    def get_contact(
        self, visible_tenants: list[str], phonebook_key: PhonebookKey, contact_uuid: str
    ) -> ContactInfo:
        return self._contact_crud.get(visible_tenants, phonebook_key, contact_uuid)

    def get_phonebook(
        self, visible_tenants: list[str], phonebook_key: PhonebookKey
    ) -> PhonebookDict:
        return self._phonebook_crud.get(visible_tenants, phonebook_key)

    def import_contacts(
        self,
        visible_tenants: list[str],
        phonebook_key: PhonebookKey,
        contacts: list[dict[str, Any]],
    ) -> tuple[list[ContactInfo], list[ContactEntryError]]:
        logger.debug(
            'Processing import of %d contacts in phonebook %s',
            len(contacts),
            phonebook_key,
        )
        to_add, errors = [], []
        for i, contact in enumerate(contacts):
            try:
                to_add.append((i, self._validate_contact(contact)))
            except InvalidContactException as ex:
                errors.append(
                    ContactEntryError(
                        contact=contact,
                        message=str(ex),
                        index=i,
                    )
                )
        if errors:
            return [], errors

        created, failed = self._contact_crud.create_many(
            visible_tenants, phonebook_key, [contact for _, contact in to_add]
        )

        return created, failed

    @staticmethod
    def _validate_contact(body: dict[str, Any]) -> dict[str, Any]:
        if not body:
            raise InvalidContactException('Contacts cannot be empty')
        if '' in body:
            raise InvalidContactException('Contacts cannot have empty keys')
        if None in body:
            raise InvalidContactException('Contacts cannot have null keys')
        body.pop('id', None)
        return body
