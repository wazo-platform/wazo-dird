# Copyright 2016-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import csv
import logging
import time
import traceback
from functools import wraps
from typing import cast
from uuid import UUID

from flask import Request, request
from xivo.tenant_flask_helpers import Tenant

from wazo_dird.auth import required_acl
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
)
from wazo_dird.http import AuthResource
from wazo_dird.plugins.phonebook_service.plugin import _PhonebookService, PhonebookKey

from .schemas import ContactListSchema, PhonebookListSchema

request: Request  # type: ignore[no-redef]

logger = logging.getLogger(__name__)


def _make_error(reason, status_code):
    return (
        {'reason': [reason], 'timestamp': [time.time()], 'status_code': status_code},
        status_code,
    )


class _Resource(AuthResource):
    def __init__(self, phonebook_service):
        self.phonebook_service: _PhonebookService = phonebook_service


def _default_error_route(f):
    @wraps(f)
    def decorator(self_, *args, **kwargs):
        try:
            return f(self_, *args, **kwargs)
        except tuple(self_.error_code_map.keys()) as e:
            logger.info('%s', e)
            logger.debug('%s', traceback.format_exc())
            code = self_.error_code_map.get(e.__class__)
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
    def post(self, phonebook_uuid: UUID):
        tenant = Tenant.autodetect()

        return (
            self.phonebook_service.create_contact(
                tenant.uuid,
                PhonebookKey(uuid=str(phonebook_uuid)),
                cast(dict, request.json),
            ),
            201,
        )

    @required_acl('dird.phonebooks.{phonebook_uuid}.contacts.read')
    @_default_error_route
    def get(self, phonebook_uuid: UUID):
        list_params: dict = ContactListSchema().load(request.args)  # type: ignore
        tenant = Tenant.autodetect()

        count = self.phonebook_service.count_contact(
            tenant.uuid,
            PhonebookKey(uuid=str(phonebook_uuid)),
            **ContactListSchema().count(request.args),
        )
        contacts = self.phonebook_service.list_contact(
            tenant.uuid, PhonebookKey(uuid=str(phonebook_uuid)), **list_params
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
    def get(self):
        tenant = Tenant.autodetect()

        list_params = cast(dict, PhonebookListSchema().load(request.args))
        count_params = cast(dict, PhonebookListSchema().count(request.args))

        count = self.phonebook_service.count_phonebook(tenant.uuid, **count_params)
        phonebooks = self.phonebook_service.list_phonebook(tenant.uuid, **list_params)

        return {'items': phonebooks, 'total': count}

    @required_acl('dird.phonebooks.create')
    @_default_error_route
    def post(self):
        tenant = Tenant.autodetect()
        body = cast(dict, request.json)
        return (
            self.phonebook_service.create_phonebook(tenant.uuid, body),
            201,
        )


class PhonebookContactImport(_Resource):
    error_code_map = {NoSuchTenant: 404, NoSuchPhonebook: 404}

    @required_acl('dird.phonebooks.{phonebook_uuid}.contacts.create')
    @_default_error_route
    def post(self, phonebook_uuid: UUID):
        tenant = Tenant.autodetect()

        charset = request.mimetype_params.get('charset', 'utf-8')
        raw_data = cast(bytes, request.data)
        try:
            data = raw_data.decode(charset).split('\n')
        except LookupError as e:
            if 'unknown encoding:' in str(e):
                return _make_error(str(e), 400)
            else:
                raise

        reader = csv.reader(data)
        fields = next(reader)
        duplicates = list({f for f in fields if fields.count(f) > 1})
        if duplicates:
            return _make_error(f'duplicate columns: {duplicates}', 400)

        to_add = [c for c in csv.DictReader(data)]
        created, failed = self.phonebook_service.import_contacts(
            tenant.uuid, PhonebookKey(uuid=str(phonebook_uuid)), to_add
        )

        return {'created': created, 'failed': failed}


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
    def get(self, phonebook_uuid: UUID, contact_uuid: UUID):
        tenant = Tenant.autodetect()

        return (
            self.phonebook_service.get_contact(
                tenant.uuid, PhonebookKey(uuid=str(phonebook_uuid)), str(contact_uuid)
            ),
            200,
        )

    @required_acl('dird.phonebooks.{phonebook_uuid}.contacts.{contact_uuid}.delete')
    @_default_error_route
    def delete(self, phonebook_uuid: UUID, contact_uuid: UUID):
        tenant = Tenant.autodetect()

        self.phonebook_service.delete_contact(
            tenant.uuid, PhonebookKey(uuid=str(phonebook_uuid)), str(contact_uuid)
        )
        return '', 204

    @required_acl('dird.phonebooks.{phonebook_uuid}.contacts.{contact_uuid}.update')
    @_default_error_route
    def put(self, phonebook_uuid: UUID, contact_uuid: UUID):
        tenant = Tenant.autodetect()
        body = cast(dict, request.json)
        return (
            self.phonebook_service.edit_contact(
                tenant.uuid,
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
    def delete(self, phonebook_uuid: UUID):
        tenant = Tenant.autodetect()

        self.phonebook_service.delete_phonebook(
            tenant.uuid, PhonebookKey(uuid=str(phonebook_uuid))
        )
        return '', 204

    @required_acl('dird.phonebooks.{phonebook_uuid}.read')
    @_default_error_route
    def get(self, phonebook_uuid: UUID):
        tenant = Tenant.autodetect()

        return (
            self.phonebook_service.get_phonebook(
                tenant.uuid, PhonebookKey(uuid=str(phonebook_uuid))
            ),
            200,
        )

    @required_acl('dird.phonebooks.{phonebook_uuid}.update')
    @_default_error_route
    def put(self, phonebook_uuid: UUID):
        tenant = Tenant.autodetect()
        body = cast(dict, request.json)
        return (
            self.phonebook_service.edit_phonebook(
                tenant.uuid,
                PhonebookKey(uuid=str(phonebook_uuid)),
                body,
            ),
            200,
        )
