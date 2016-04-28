# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import cStringIO
import logging
import re

from functools import wraps
from flask import request
from flask import Response
from flask_restful import reqparse
from time import time

from xivo.unicode_csv import UnicodeDictReader
from xivo.unicode_csv import UnicodeDictWriter
from xivo_dird import BaseViewPlugin
from xivo_dird.core import auth
from xivo_dird.core.auth import required_acl
from xivo_dird.core.rest_api import api
from xivo_dird.core.rest_api import AuthResource

logger = logging.getLogger(__name__)

CHARSET_REGEX = re.compile('.*; *charset *= *(.*)')


def catch_service_error(wrapped):
    @wraps(wrapped)
    def wrapper(self, *args, **kwargs):
        try:
            return wrapped(self, *args, **kwargs)
        except self.personal_service.PersonalServiceException as e:
            error = {
                'reason': [str(e)],
                'timestamp': [time()],
                'status_code': 503,
            }
            return error, 503
    return wrapper


class PersonalViewPlugin(BaseViewPlugin):

    personal_all_url = '/personal'
    personal_one_url = '/personal/<contact_id>'
    personal_import_url = '/personal/import'

    def load(self, args=None):
        personal_service = args['services'].get('personal')
        if personal_service:
            PersonalAll.configure(personal_service)
            PersonalOne.configure(personal_service)
            PersonalImport.configure(personal_service)
            api.add_resource(PersonalAll, self.personal_all_url)
            api.add_resource(PersonalOne, self.personal_one_url)
            api.add_resource(PersonalImport, self.personal_import_url)


parser = reqparse.RequestParser()
parser.add_argument('format', type=unicode, required=False, location='args')


class PersonalAll(AuthResource):

    personal_service = None

    @classmethod
    def configure(cls, personal_service):
        cls.personal_service = personal_service

    @required_acl('dird.personal.create')
    @catch_service_error
    def post(self):
        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        contact = request.json
        try:
            contact = self.personal_service.create_contact(contact, token_infos)
            return contact, 201
        except self.personal_service.InvalidPersonalContact as e:
            error = {
                'reason': e.errors,
                'timestamp': [time()],
                'status_code': 400,
            }
            return error, 400

    @required_acl('dird.personal.read')
    @catch_service_error
    def get(self):
        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)

        contacts = self.personal_service.list_contacts_raw(token_infos)

        mimetype = request.mimetype
        if not mimetype:
            args = parser.parse_args()
            mimetype = args.get('format', None)

        return self.contacts_formatter(mimetype)(contacts)

    @required_acl('dird.personal.delete')
    @catch_service_error
    def delete(self):
        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)

        self.personal_service.purge_contacts(token_infos)

        return '', 204

    @classmethod
    def contacts_formatter(cls, mimetype):
        formatters = {
            'text/csv': cls.format_csv,
            'application/json': cls.format_json
        }
        return formatters.get(mimetype, cls.format_json)

    @staticmethod
    def format_csv(contacts):
        if not contacts:
            return '', 204
        csv_text = cStringIO.StringIO()
        fieldnames = sorted(list(set(attribute for contact in contacts for attribute in contact)))
        for contact in contacts:
            for attribute in contact:
                if contact[attribute] is None:
                    contact[attribute] = ''
        csv_writer = UnicodeDictWriter(csv_text, fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(contacts)
        return Response(response=csv_text.getvalue(),
                        status=200,
                        content_type='text/csv; charset=utf-8')

    @staticmethod
    def format_json(contacts):
        return {'items': contacts}, 200


class PersonalOne(AuthResource):

    personal_service = None

    @classmethod
    def configure(cls, personal_service):
        cls.personal_service = personal_service

    @required_acl('dird.personal.{contact_id}.read')
    @catch_service_error
    def get(self, contact_id):
        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        try:
            contact = self.personal_service.get_contact(contact_id, token_infos)
            return contact, 200
        except self.personal_service.NoSuchPersonalContact as e:
            error = {
                'reason': [str(e)],
                'timestamp': [time()],
                'status_code': 404,
            }
            return error, 404

    @required_acl('dird.personal.{contact_id}.update')
    @catch_service_error
    def put(self, contact_id):
        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        new_contact = request.json
        try:
            contact = self.personal_service.edit_contact(contact_id, new_contact, token_infos)
            return contact, 200
        except self.personal_service.NoSuchPersonalContact as e:
            error = {
                'reason': [str(e)],
                'timestamp': [time()],
                'status_code': 404,
            }
            return error, 404
        except self.personal_service.InvalidPersonalContact as e:
            error = {
                'reason': e.errors,
                'timestamp': [time()],
                'status_code': 400,
            }
            return error, 400

    @required_acl('dird.personal.{contact_id}.delete')
    @catch_service_error
    def delete(self, contact_id):
        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        try:
            self.personal_service.remove_contact(contact_id, token_infos)
            return '', 204
        except self.personal_service.NoSuchPersonalContact as e:
            error = {
                'reason': [str(e)],
                'timestamp': [time()],
                'status_code': 404,
            }
            return error, 404


class PersonalImport(AuthResource):

    personal_service = None

    @classmethod
    def configure(cls, personal_service):
        cls.personal_service = personal_service

    @required_acl('dird.personal.import.create')
    def post(self):
        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)

        charset = request.mimetype_params.get('charset', 'utf-8')
        csv_document = request.data
        try:
            csv_document.decode(charset)
        except UnicodeDecodeError as e:
            error = {
                'reason': [str(e)],
                'timestamp': [time()],
                'status_code': 400,
            }
            return error, 400

        created, errors = self._mass_import(csv_document, charset, token_infos)

        if not created:
            error = {
                'reason': errors or ['No contact found'],
                'timestamp': [time()],
                'status_code': 400,
            }
            return error, 400

        result = {
            'created': created,
            'failed': errors,
        }
        return result, 201

    def _mass_import(self, csv_document, encoding, token_infos):
        reader = UnicodeDictReader(csv_document.split('\n'), encoding=encoding)
        return self.personal_service.create_contacts(reader, token_infos)
