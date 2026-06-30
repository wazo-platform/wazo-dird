# Copyright 2016-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import csv
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast
from uuid import UUID

from flask import Request, request
from xivo.tenant_flask_helpers import Tenant

from wazo_dird.auth import required_acl
from wazo_dird.database.queries.base import ContactInfo
from wazo_dird.database.queries.phonebook import PhonebookDict, PhonebookKey
from wazo_dird.exception import (
    DatabaseServiceUnavailable,
    DuplicatedContactException,
    DuplicatedPhonebookException,
    InvalidArgumentError,
    InvalidContactException,
    InvalidPhonebookException,
    NoSuchContact,
    NoSuchPhonebook,
    NoSuchTenant,
    PhonebookContactImportAPIError,
)
from wazo_dird.http import AuthResource, get_json_body
from wazo_dird.plugin_helpers.tenant import get_tenant_uuids
from wazo_dird.plugins.phonebook_service.plugin import _PhonebookService

from .schemas import contact_list_schema, phonebook_list_schema

R = TypeVar('R')

ErrorResponse = tuple[dict[str, Any], int]

request: Request  # type: ignore[no-redef]

logger = logging.getLogger(__name__)


def _make_error(reason: str, status_code: int) -> ErrorResponse:
    return (
        {'reason': [reason], 'timestamp': [time.time()], 'status_code': status_code},
        status_code,
    )


class _Resource(AuthResource):
    error_code_map: dict[type[Exception], int] = {}

    def __init__(self, phonebook_service: _PhonebookService) -> None:
        self.phonebook_service: _PhonebookService = phonebook_service


def _default_error_route(
    f: Callable[..., R],
) -> Callable[..., R | ErrorResponse]:
    @wraps(f)
    def decorator(self_: _Resource, *args: Any, **kwargs: Any) -> R | ErrorResponse:
        try:
            return f(self_, *args, **kwargs)
        except tuple(self_.error_code_map.keys()) as e:
            logger.info('%s', e)
            code = self_.error_code_map.get(e.__class__)
            assert code is not None
            return _make_error(str(e), code)

    return decorator


class PhonebookContactAll(_Resource):
    error_code_map = {
        InvalidArgumentError: 400,
        InvalidContactException: 400,
        NoSuchPhonebook: 404,
        DatabaseServiceUnavailable: 503,
        DuplicatedContactException: 409,
        NoSuchTenant: 404,
    }

    @required_acl('dird.phonebooks.{phonebook_uuid}.contacts.create')
    @_default_error_route
    def post(self, phonebook_uuid: UUID) -> tuple[ContactInfo, int]:
        visible_tenants = get_tenant_uuids(recurse=False)

        return (
            self.phonebook_service.create_contact(
                visible_tenants,
                PhonebookKey(uuid=str(phonebook_uuid)),
                get_json_body(),
            ),
            201,
        )

    @required_acl('dird.phonebooks.{phonebook_uuid}.contacts.read')
    @_default_error_route
    def get(self, phonebook_uuid: UUID) -> tuple[dict[str, Any], int]:
        list_params: dict[str, Any] = contact_list_schema.load(request.args)
        visible_tenants = get_tenant_uuids(recurse=False)

        count = self.phonebook_service.count_contact(
            visible_tenants,
            PhonebookKey(uuid=str(phonebook_uuid)),
            **contact_list_schema.load_count(request.args),
        )
        list_params.pop("recurse")
        contacts = self.phonebook_service.list_contacts(
            visible_tenants, PhonebookKey(uuid=str(phonebook_uuid)), **list_params
        )

        return {'items': contacts, 'total': count}, 200


class PhonebookAll(_Resource):
    error_code_map = {
        InvalidArgumentError: 400,
        DuplicatedPhonebookException: 409,
        DatabaseServiceUnavailable: 503,
        InvalidPhonebookException: 400,
        NoSuchTenant: 404,
    }

    @required_acl('dird.phonebooks.read')
    @_default_error_route
    def get(self) -> tuple[dict[str, Any], int]:
        list_params = cast('dict[str, Any]', phonebook_list_schema.load(request.args))
        count_params = phonebook_list_schema.load_count(request.args)
        visible_tenants = get_tenant_uuids(recurse=list_params.pop('recurse'))

        count = self.phonebook_service.count_phonebook(visible_tenants, **count_params)
        phonebooks = self.phonebook_service.list_phonebook(
            visible_tenants, **list_params
        )

        return {'items': phonebooks, 'total': count}, 200

    @required_acl('dird.phonebooks.create')
    @_default_error_route
    def post(self) -> tuple[PhonebookDict, int]:
        tenant = Tenant.autodetect()
        body = get_json_body()
        return (
            self.phonebook_service.create_phonebook(tenant.uuid, body),
            201,
        )


class PhonebookContactImport(_Resource):
    error_code_map = {NoSuchTenant: 404, NoSuchPhonebook: 404}

    @required_acl('dird.phonebooks.{phonebook_uuid}.contacts.create')
    @_default_error_route
    def post(self, phonebook_uuid: UUID) -> tuple[dict[str, Any], int]:
        visible_tenants = get_tenant_uuids(recurse=False)

        charset = request.mimetype_params.get('charset', 'utf-8')
        raw_data = cast(bytes, request.data)
        logger.debug('len(raw_data)=%d', len(raw_data))
        try:
            data = raw_data.decode(charset).split('\n')
        except LookupError as e:
            if 'unknown encoding:' in str(e):
                raise PhonebookContactImportAPIError(
                    message=f'bad input encoding: {str(e)}',
                    error_id='phonebook-contact-import-bad-encoding',
                    status_code=400,
                    details={'error': str(e), 'charset': charset},
                )
            else:
                raise

        reader = csv.DictReader(data)
        fields = reader.fieldnames or []
        duplicates = list({f for f in fields if fields.count(f) > 1})
        if duplicates:
            raise PhonebookContactImportAPIError(
                message=f'duplicate columns: {duplicates}',
                error_id='phonebook-contact-import-duplicate-columns',
                status_code=400,
                details={'duplicates': duplicates},
            )

        try:
            to_add = [c for c in reader]
        except csv.Error as e:
            raise PhonebookContactImportAPIError(
                message=f'invalid contact import file: {str(e)}',
                error_id='phonebook-contact-import-invalid-file',
                status_code=400,
                details={'error': str(e)},
            )

        if not to_add:
            raise PhonebookContactImportAPIError(
                message='empty contact import file',
                error_id='phonebook-contact-import-empty-file',
                status_code=400,
                details={'line_count': len(data), 'byte_count': len(raw_data)},
            )

        created, failed = self.phonebook_service.import_contacts(
            visible_tenants, PhonebookKey(uuid=str(phonebook_uuid)), to_add
        )
        if failed:
            raise PhonebookContactImportAPIError(
                message='failed to create contacts',
                error_id='phonebook-contact-import-bad-contacts',
                status_code=400,
                details={'errors': failed},
            )

        return {'created': created, 'failed': failed}, 201


class PhonebookContactOne(_Resource):
    error_code_map = {
        DuplicatedContactException: 409,
        InvalidContactException: 400,
        DatabaseServiceUnavailable: 503,
        NoSuchContact: 404,
        NoSuchPhonebook: 404,
        NoSuchTenant: 404,
    }

    @required_acl('dird.phonebooks.{phonebook_uuid}.contacts.{contact_uuid}.read')
    @_default_error_route
    def get(self, phonebook_uuid: UUID, contact_uuid: UUID) -> tuple[ContactInfo, int]:
        visible_tenants = get_tenant_uuids(recurse=False)

        return (
            self.phonebook_service.get_contact(
                visible_tenants,
                PhonebookKey(uuid=str(phonebook_uuid)),
                str(contact_uuid),
            ),
            200,
        )

    @required_acl('dird.phonebooks.{phonebook_uuid}.contacts.{contact_uuid}.delete')
    @_default_error_route
    def delete(self, phonebook_uuid: UUID, contact_uuid: UUID) -> tuple[str, int]:
        visible_tenants = get_tenant_uuids(recurse=False)

        self.phonebook_service.delete_contact(
            visible_tenants, PhonebookKey(uuid=str(phonebook_uuid)), str(contact_uuid)
        )
        return '', 204

    @required_acl('dird.phonebooks.{phonebook_uuid}.contacts.{contact_uuid}.update')
    @_default_error_route
    def put(self, phonebook_uuid: UUID, contact_uuid: UUID) -> tuple[ContactInfo, int]:
        visible_tenants = get_tenant_uuids(recurse=False)
        body = get_json_body()
        return (
            self.phonebook_service.edit_contact(
                visible_tenants,
                PhonebookKey(uuid=str(phonebook_uuid)),
                str(contact_uuid),
                body,
            ),
            200,
        )


class PhonebookOne(_Resource):
    error_code_map = {
        DatabaseServiceUnavailable: 503,
        DuplicatedPhonebookException: 409,
        InvalidPhonebookException: 400,
        NoSuchPhonebook: 404,
        NoSuchTenant: 404,
    }

    @required_acl('dird.phonebooks.{phonebook_uuid}.delete')
    @_default_error_route
    def delete(self, phonebook_uuid: UUID) -> tuple[str, int]:
        visible_tenants = get_tenant_uuids(recurse=False)

        self.phonebook_service.delete_phonebook(
            visible_tenants, PhonebookKey(uuid=str(phonebook_uuid))
        )
        return '', 204

    @required_acl('dird.phonebooks.{phonebook_uuid}.read')
    @_default_error_route
    def get(self, phonebook_uuid: UUID) -> tuple[PhonebookDict, int]:
        visible_tenants = get_tenant_uuids(recurse=False)

        return (
            self.phonebook_service.get_phonebook(
                visible_tenants, PhonebookKey(uuid=str(phonebook_uuid))
            ),
            200,
        )

    @required_acl('dird.phonebooks.{phonebook_uuid}.update')
    @_default_error_route
    def put(self, phonebook_uuid: UUID) -> tuple[PhonebookDict, int]:
        visible_tenants = get_tenant_uuids(recurse=False)
        body = get_json_body()
        return (
            self.phonebook_service.edit_phonebook(
                visible_tenants,
                PhonebookKey(uuid=str(phonebook_uuid)),
                body,
            ),
            200,
        )
