# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Avencall
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

import time

from flask import request

from xivo_dird import BaseViewPlugin
from xivo_dird.core import auth
from xivo_dird.core.exception import InvalidContactException, InvalidPhonebookException
from xivo_dird.core.rest_api import api, AuthResource
from xivo_dird.database import DuplicatedContactException, DuplicatedPhonebookException, NoSuchPhonebook


def _make_error(reason, status_code):
    return {'reason': [reason],
            'timestamp': [time.time()],
            'status_code': status_code}, status_code


class PhonebookViewPlugin(BaseViewPlugin):

    phonebook_all_url = '/tenants/<string:tenant>/phonebooks'
    phonebook_one_url = '/tenants/<string:tenant>/phonebooks/<int:phonebook_id>'
    contact_all_url = '/tenants/<string:tenant>/phonebooks/<int:phonebook_id>/contacts'
    contact_one_url = '/tenants/<string:tenant>/phonebooks/<int:phonebook_id>/contacts/<contact_uuid>'

    def load(self, args=None):
        phonebook_service = args['services'].get('phonebook')
        if phonebook_service:
            ContactAll.configure(phonebook_service)
            ContactOne.configure(phonebook_service)
            PhonebookAll.configure(phonebook_service)
            PhonebookOne.configure(phonebook_service)
            api.add_resource(ContactAll, self.contact_all_url)
            api.add_resource(ContactOne, self.contact_one_url)
            api.add_resource(PhonebookAll, self.phonebook_all_url)
            api.add_resource(PhonebookOne, self.phonebook_one_url)


class _Resource(AuthResource):

    phonebook_service = None

    @classmethod
    def configure(cls, phonebook_service):
        cls.phonebook_service = phonebook_service


class _ArgParser(object):

    def __init__(self, args):
        self._search = args.get('search')
        self._direction = args.get('direction')
        self._limit = int(args.get('limit', 0))
        self._offset = int(args.get('offset', 0))
        self._order = args.get('order')

    def count_params(self):
        params = {}
        if self._search:
            params['search'] = self._search
        return params

    def list_params(self):
        params = self.count_params()
        if self._direction:
            params['direction'] = self._direction
        if self._order:
            params['order'] = self._order
        if self._limit:
            params['limit'] = self._limit
        if self._offset:
            params['offset'] = self._offset
        return params


class ContactAll(_Resource):

    _error_code_map = {InvalidContactException: 400,
                       NoSuchPhonebook: 404,
                       DuplicatedContactException: 409}

    @auth.required_acl('dird.tenants.{tenant}.phonebooks.{phonebook_id}.contacts.create')
    def post(self, tenant, phonebook_id):
        try:
            return self.phonebook_service.create_contact(tenant, phonebook_id, request.json), 201
        except tuple(self._error_code_map.keys()) as e:
            code = self._error_code_map.get(e.__class__)
            return _make_error(str(e), code)

    @auth.required_acl('dird.tenants.{tenant}.phonebooks.{phonebook_id}.contacts.read')
    def get(self, tenant, phonebook_id):
        parser = _ArgParser(request.args)
        try:
            count = self.phonebook_service.count_contact(tenant, phonebook_id, **parser.count_params())
            contacts = self.phonebook_service.list_contact(tenant, phonebook_id, **parser.list_params())
        except tuple(self._error_code_map.keys()) as e:
            code = self._error_code_map.get(e.__class__)
            return _make_error(str(e), code)

        return {'items': contacts, 'total': count}, 200


class ContactOne(_Resource):
    pass


class PhonebookAll(_Resource):

    @auth.required_acl('dird.tenants.{tenant}.phonebooks.read')
    def get(self, tenant):
        parser = _ArgParser(request.args)
        count = self.phonebook_service.count_phonebook(tenant, **parser.count_params())
        phonebooks = self.phonebook_service.list_phonebook(tenant, **parser.list_params())

        return {'items': phonebooks,
                'total': count}

    @auth.required_acl('dird.tenants.{tenant}.phonebooks.create')
    def post(self, tenant):
        try:
            new_phonebook = self.phonebook_service.create_phonebook(tenant, request.json)
        except DuplicatedPhonebookException:
            return _make_error('Adding this phonebook would create a duplicate', 409)
        except InvalidPhonebookException as e:
            return _make_error(e.errors, 400)

        return new_phonebook, 201


class PhonebookOne(_Resource):

    @auth.required_acl('dird.tenants.{tenant}.phonebooks.{phonebook_id}.delete')
    def delete(self, tenant, phonebook_id):
        try:
            self.phonebook_service.delete_phonebook(tenant, phonebook_id)
        except NoSuchPhonebook as e:
            return _make_error(str(e), 404)

        return '', 204

    @auth.required_acl('dird.tenants.{tenant}.phonebooks.{phonebook_id}.read')
    def get(self, tenant, phonebook_id):
        try:
            return self.phonebook_service.get_phonebook(tenant, phonebook_id), 200
        except NoSuchPhonebook as e:
            return _make_error(str(e), 404)

    @auth.required_acl('dird.tenants.{tenant}.phonebooks.{phonebook_id}.update')
    def put(self, tenant, phonebook_id):
        try:
            return self.phonebook_service.edit_phonebook(tenant, phonebook_id, request.json), 200
        except NoSuchPhonebook as e:
            return _make_error(str(e), 404)
        except InvalidPhonebookException as e:
            return _make_error(e.errors, 400)
        except DuplicatedPhonebookException:
            return _make_error('Adding this phonebook would create a duplicate', 409)
