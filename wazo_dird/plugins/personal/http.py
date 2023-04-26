# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import csv
import io
import logging
import re

from flask import request
from flask import Response
from flask_restful import reqparse
from time import time

from xivo.rest_api_helpers import APIException

from wazo_dird import auth
from wazo_dird.auth import required_acl
from wazo_dird.http import LegacyAuthResource

logger = logging.getLogger(__name__)

CHARSET_REGEX = re.compile('.*; *charset *= *(.*)')


parser = reqparse.RequestParser()
parser.add_argument('format', type=str, required=False, location='args')


def _get_calling_user_uuid():
    token = request.headers['X-Auth-Token']
    token_infos = auth.client().token.get(token)
    user_uuid = token_infos.get('metadata').get('uuid')
    if not user_uuid:
        raise APIException(401, 'This token has no user UUID', 'invalid-token')

    return user_uuid


class PersonalAll(LegacyAuthResource):
    personal_service = None

    @classmethod
    def configure(cls, personal_service):
        cls.personal_service = personal_service

    @required_acl('dird.personal.create')
    def post(self):
        user_uuid = _get_calling_user_uuid()
        contact = request.json
        try:
            contact = self.personal_service.create_contact(contact, user_uuid)
            return contact, 201
        except self.personal_service.InvalidPersonalContact as e:
            error = {'reason': e.errors, 'timestamp': [time()], 'status_code': 400}
            return error, 400
        except self.personal_service.DuplicatedContactException:
            error = {
                'reason': ['Addind this contact would create a duplicate'],
                'timestamp': [time()],
                'status_code': 409,
            }
            return error, 409

    @required_acl('dird.personal.read')
    def get(self):
        user_uuid = _get_calling_user_uuid()

        contacts = self.personal_service.list_contacts_raw(user_uuid)

        mimetype = request.mimetype
        if not mimetype:
            args = parser.parse_args()
            mimetype = args.get('format', None)

        return self.contacts_formatter(mimetype)(contacts)

    @required_acl('dird.personal.delete')
    def delete(self):
        user_uuid = _get_calling_user_uuid()

        self.personal_service.purge_contacts(user_uuid)

        return '', 204

    @classmethod
    def contacts_formatter(cls, mimetype):
        formatters = {'text/csv': cls.format_csv, 'application/json': cls.format_json}
        return formatters.get(mimetype, cls.format_json)

    @staticmethod
    def format_csv(contacts):
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
    def format_json(contacts):
        return {'items': contacts}, 200


class PersonalOne(LegacyAuthResource):
    personal_service = None

    @classmethod
    def configure(cls, personal_service):
        cls.personal_service = personal_service

    @required_acl('dird.personal.{contact_id}.read')
    def get(self, contact_id):
        user_uuid = _get_calling_user_uuid()
        try:
            contact = self.personal_service.get_contact(contact_id, user_uuid)
            return contact, 200
        except self.personal_service.NoSuchContact as e:
            error = {'reason': [str(e)], 'timestamp': [time()], 'status_code': 404}
            return error, 404

    @required_acl('dird.personal.{contact_id}.update')
    def put(self, contact_id):
        user_uuid = _get_calling_user_uuid()
        new_contact = request.json
        try:
            contact = self.personal_service.edit_contact(
                contact_id, new_contact, user_uuid
            )
            return contact, 200
        except self.personal_service.NoSuchContact as e:
            error = {'reason': [str(e)], 'timestamp': [time()], 'status_code': 404}
            return error, 404
        except self.personal_service.InvalidPersonalContact as e:
            error = {'reason': e.errors, 'timestamp': [time()], 'status_code': 400}
            return error, 400
        except self.personal_service.DuplicatedContactException:
            error = {
                'reason': ['Modifying this contact would create a duplicate'],
                'timestamp': [time()],
                'status_code': 409,
            }
            return error, 409

    @required_acl('dird.personal.{contact_id}.delete')
    def delete(self, contact_id):
        user_uuid = _get_calling_user_uuid()
        try:
            self.personal_service.remove_contact(contact_id, user_uuid)
            return '', 204
        except self.personal_service.NoSuchContact as e:
            error = {'reason': [str(e)], 'timestamp': [time()], 'status_code': 404}
            return error, 404


class PersonalImport(LegacyAuthResource):
    personal_service = None

    @classmethod
    def configure(cls, personal_service):
        cls.personal_service = personal_service

    @required_acl('dird.personal.import.create')
    def post(self):
        user_uuid = _get_calling_user_uuid()

        charset = request.mimetype_params.get('charset', 'utf-8')
        try:
            csv_document = request.data.decode(charset)
        except UnicodeDecodeError as e:
            error = {'reason': [str(e)], 'timestamp': [time()], 'status_code': 400}
            return error, 400

        created, errors = self._mass_import(csv_document, user_uuid)

        if not created:
            error = {
                'reason': errors or ['No contact found'],
                'timestamp': [time()],
                'status_code': 400,
            }
            return error, 400

        result = {'created': created, 'failed': errors}
        return result, 201

    def _mass_import(self, csv_document, user_uuid):
        reader = csv.DictReader(csv_document.split('\n'))
        return self.personal_service.create_contacts(reader, user_uuid)
