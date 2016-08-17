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
from functools import wraps

from xivo_dird import BaseViewPlugin
from xivo_dird.core import auth
from xivo_dird.core.exception import InvalidArgumentError, InvalidContactException, InvalidPhonebookException
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
        self._direction = self._get_string_from_valid_values(args, 'direction', ['asc', 'desc', None])
        self._limit = self._get_positive_int(args, 'limit')
        self._offset = self._get_positive_int(args, 'offset')
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

    @staticmethod
    def _get_string_from_valid_values(args, name, valid_values):
        value = args.get(name)
        if value in valid_values:
            return value

        raise InvalidArgumentError('{} should be one of {}'.format(name, valid_values))

    @staticmethod
    def _get_positive_int(args, name):
        try:
            value = int(args.get(name, 0))
            if value >= 0:
                return value
        except ValueError:
            pass

        raise InvalidArgumentError('{} should be a positive integer'.format(name))


def _default_error_route(f):

    @wraps(f)
    def decorator(self_, *args, **kwargs):
        try:
            return f(self_, *args, **kwargs)
        except tuple(self_.error_code_map.keys()) as e:
            code = self_.error_code_map.get(e.__class__)
            return _make_error(str(e), code)
    return decorator


class ContactAll(_Resource):

    error_code_map = {InvalidContactException: 400,
                      NoSuchPhonebook: 404,
                      DuplicatedContactException: 409}

    @auth.required_acl('dird.tenants.{tenant}.phonebooks.{phonebook_id}.contacts.create')
    @_default_error_route
    def post(self, tenant, phonebook_id):
        return self.phonebook_service.create_contact(tenant, phonebook_id, request.json), 201

    @auth.required_acl('dird.tenants.{tenant}.phonebooks.{phonebook_id}.contacts.read')
    @_default_error_route
    def get(self, tenant, phonebook_id):
        parser = _ArgParser(request.args)
        count = self.phonebook_service.count_contact(tenant, phonebook_id, **parser.count_params())
        contacts = self.phonebook_service.list_contact(tenant, phonebook_id, **parser.list_params())

        return {'items': contacts,
                'total': count}, 200


class ContactOne(_Resource):
    pass


class PhonebookAll(_Resource):

    error_code_map = {DuplicatedPhonebookException: 409,
                      InvalidPhonebookException: 400}

    @auth.required_acl('dird.tenants.{tenant}.phonebooks.read')
    def get(self, tenant):
        parser = _ArgParser(request.args)
        count = self.phonebook_service.count_phonebook(tenant, **parser.count_params())
        phonebooks = self.phonebook_service.list_phonebook(tenant, **parser.list_params())

        return {'items': phonebooks,
                'total': count}

    @auth.required_acl('dird.tenants.{tenant}.phonebooks.create')
    @_default_error_route
    def post(self, tenant):
        return self.phonebook_service.create_phonebook(tenant, request.json), 201


class PhonebookOne(_Resource):

    error_code_map = {DuplicatedPhonebookException: 409,
                      InvalidPhonebookException: 400,
                      NoSuchPhonebook: 404}

    @auth.required_acl('dird.tenants.{tenant}.phonebooks.{phonebook_id}.delete')
    @_default_error_route
    def delete(self, tenant, phonebook_id):
        self.phonebook_service.delete_phonebook(tenant, phonebook_id)
        return '', 204

    @auth.required_acl('dird.tenants.{tenant}.phonebooks.{phonebook_id}.read')
    @_default_error_route
    def get(self, tenant, phonebook_id):
        return self.phonebook_service.get_phonebook(tenant, phonebook_id), 200

    @auth.required_acl('dird.tenants.{tenant}.phonebooks.{phonebook_id}.update')
    @_default_error_route
    def put(self, tenant, phonebook_id):
        return self.phonebook_service.edit_phonebook(tenant, phonebook_id, request.json), 200
