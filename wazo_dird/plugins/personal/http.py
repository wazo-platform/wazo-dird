# Copyright 2015-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import csv
import io
import logging
import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from flask import Response, request
from flask_restful import reqparse
from xivo.rest_api_helpers import APIException
from xivo.tenant_flask_helpers import Tenant

from wazo_dird.auth import get_user_uuid, required_acl
from wazo_dird.exception import (
    DuplicatedPersonalContact,
    InvalidPersonalContactAPIException,
    NoSuchPersonalContact,
)
from wazo_dird.http import AuthResource, get_json_body
from wazo_dird.schemas import UncheckedOrderListSchema

if TYPE_CHECKING:
    from wazo_dird.database.queries.base import ContactInfo
    from wazo_dird.plugins.personal_service.plugin import _PersonalService

logger = logging.getLogger(__name__)

list_schema = UncheckedOrderListSchema()

CHARSET_REGEX = re.compile('.*; *charset *= *(.*)')


parser = reqparse.RequestParser()
parser.add_argument('format', type=str, required=False, location='args')


class PersonalAll(AuthResource):
    personal_service: _PersonalService

    @classmethod
    def configure(cls, personal_service: _PersonalService) -> None:
        cls.personal_service = personal_service

    @required_acl('dird.personal.create')
    def post(self) -> tuple[dict[str, Any] | None, int]:
        user_uuid = get_user_uuid()
        tenant_uuid = Tenant.autodetect().uuid
        contact = get_json_body()
        try:
            created = self.personal_service.create_contact(
                contact, user_uuid, tenant_uuid
            )
            return created, 201
        except self.personal_service.InvalidPersonalContact as e:
            raise InvalidPersonalContactAPIException(e.errors) from e
        except self.personal_service.DuplicatedContactException as e:
            raise DuplicatedPersonalContact(
                'Adding this contact would create a duplicate'
            ) from e

    @required_acl('dird.personal.read')
    def get(
        self,
    ) -> tuple[dict[str, Any], int] | tuple[str, int] | Response:
        user_uuid = get_user_uuid()
        search_params = list_schema.load(request.args)
        try:
            contacts = self.personal_service.list_contacts_raw(
                user_uuid, search_params=search_params
            )
        except ValueError as e:
            raise APIException(400, str(e), 'invalid-data', resource='personal') from e

        mimetype = request.mimetype
        if not mimetype:
            args = parser.parse_args()
            mimetype = args.get('format', None)

        return self.contacts_formatter(mimetype)(contacts)

    @required_acl('dird.personal.delete')
    def delete(self) -> tuple[str, int]:
        user_uuid = get_user_uuid()

        self.personal_service.purge_contacts(user_uuid)

        return '', 204

    @classmethod
    def contacts_formatter(
        cls, mimetype: str | None
    ) -> Callable[
        [list[dict[str, Any]]],
        tuple[dict[str, Any], int] | tuple[str, int] | Response,
    ]:
        formatters: dict[
            str,
            Callable[
                [list[dict[str, Any]]],
                tuple[dict[str, Any], int] | tuple[str, int] | Response,
            ],
        ] = {'text/csv': cls.format_csv, 'application/json': cls.format_json}
        if mimetype is None:
            return cls.format_json
        return formatters.get(mimetype, cls.format_json)

    @staticmethod
    def format_csv(
        contacts: list[dict[str, Any]],
    ) -> tuple[str, int] | Response:
        if not contacts:
            return '', 204
        csv_text = io.StringIO()
        fieldnames = sorted(
            list({attribute for contact in contacts for attribute in contact})
        )
        for contact in contacts:
            for attribute in contact:
                if contact[attribute] is None:
                    contact[attribute] = ''
        csv_writer = csv.DictWriter(csv_text, fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(contacts)
        return Response(
            response=csv_text.getvalue(),
            status=200,
            content_type='text/csv; charset=utf-8',
        )

    @staticmethod
    def format_json(
        contacts: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], int]:
        return {'items': contacts}, 200


class PersonalOne(AuthResource):
    personal_service: _PersonalService

    @classmethod
    def configure(cls, personal_service: _PersonalService) -> None:
        cls.personal_service = personal_service

    @required_acl('dird.personal.{contact_id}.read')
    def get(
        self, contact_id: str
    ) -> tuple[ContactInfo, int] | tuple[dict[str, Any], int]:
        user_uuid = get_user_uuid()
        try:
            contact = self.personal_service.get_contact(contact_id, user_uuid)
            return contact, 200
        except self.personal_service.NoSuchContact as e:
            raise NoSuchPersonalContact(contact_id) from e

    @required_acl('dird.personal.{contact_id}.update')
    def put(self, contact_id: str) -> tuple[dict[str, Any] | None, int]:
        user_uuid = get_user_uuid()
        tenant_uuid = Tenant.autodetect().uuid
        new_contact = get_json_body()
        try:
            contact = self.personal_service.edit_contact(
                contact_id, new_contact, user_uuid, tenant_uuid
            )
            return contact, 200
        except self.personal_service.NoSuchContact as e:
            raise NoSuchPersonalContact(contact_id) from e
        except self.personal_service.InvalidPersonalContact as e:
            raise InvalidPersonalContactAPIException(e.errors) from e
        except self.personal_service.DuplicatedContactException as e:
            raise DuplicatedPersonalContact(
                'Modifying this contact would create a duplicate'
            ) from e

    @required_acl('dird.personal.{contact_id}.delete')
    def delete(self, contact_id: str) -> tuple[str | dict[str, Any], int]:
        user_uuid = get_user_uuid()
        try:
            self.personal_service.remove_contact(contact_id, user_uuid)
            return '', 204
        except self.personal_service.NoSuchContact as e:
            raise NoSuchPersonalContact(contact_id) from e


class PersonalImport(AuthResource):
    personal_service: _PersonalService

    @classmethod
    def configure(cls, personal_service: _PersonalService) -> None:
        cls.personal_service = personal_service

    @required_acl('dird.personal.import.create')
    def post(self) -> tuple[dict[str, Any], int]:
        user_uuid = get_user_uuid()
        tenant_uuid = Tenant.autodetect().uuid

        charset = request.mimetype_params.get('charset', 'utf-8')
        try:
            csv_document = request.data.decode(charset)
        except UnicodeDecodeError as e:
            raise APIException(400, str(e), 'invalid-data', resource='personal') from e

        created, errors = self._mass_import(csv_document, user_uuid, tenant_uuid)

        if not created:
            raise APIException(
                400,
                'No contact imported' if errors else 'No contact found',
                'invalid-data',
                {'failed': errors},
                'personal',
            )

        result = {'created': created, 'failed': errors}
        return result, 201

    def _mass_import(
        self, csv_document: str, user_uuid: str, tenant_uuid: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        reader = csv.DictReader(csv_document.split('\n'))
        return self.personal_service.create_contacts(reader, user_uuid, tenant_uuid)
