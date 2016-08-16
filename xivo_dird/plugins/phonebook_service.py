# -*- coding: utf-8 -*-

# Copyright (C) 2016 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from marshmallow import fields, Schema, validate

from xivo_dird import BaseServicePlugin, database
from xivo_dird.core.exception import InvalidPhonebookException

logger = logging.getLogger(__name__)


class _PhonebookSchema(Schema):
    name = fields.String(validate=validate.Length(min=1, max=255), required=True)
    description = fields.String(allow_none=True)


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
        return _PhonebookService(database.PhonebookCRUD(Session),
                                 database.PhonebookContactCRUD(Session))

    def _new_db_session(self, db_uri):
        self._Session = scoped_session(sessionmaker())
        engine = create_engine(db_uri)
        self._Session.configure(bind=engine)
        return self._Session


class _PhonebookService(object):

    def __init__(self, phonebook_crud, contact_crud):
        self._phonebook_crud = phonebook_crud
        self._contact_crud = contact_crud

    def list_contact(self, tenant, phonebook_id, limit=None, offset=None,
                     order=None, direction=None, **params):
        results = self._contact_crud.list(tenant, phonebook_id, **params)
        if order:
            reverse = direction == 'desc'
            results = sorted(results, key=lambda x: x.get(order), reverse=reverse)
        if offset:
            results = results[offset:]
        if limit:
            results = results[:limit]
        return results

    def list_phonebook(self, tenant, **params):
        return self._phonebook_crud.list(tenant, **params)

    def count_contact(self, tenant, phonebook_id, **params):
        return self._contact_crud.count(tenant, phonebook_id, **params)

    def count_phonebook(self, tenant, **params):
        return self._phonebook_crud.count(tenant, **params)

    def create_contact(self, tenant, phonebook_id, contact_info):
        return self._contact_crud.create(tenant, phonebook_id, contact_info)

    def create_phonebook(self, tenant, phonebook_info):
        body, errors = _PhonebookSchema().load(phonebook_info)
        if errors:
            raise InvalidPhonebookException(errors)
        return self._phonebook_crud.create(tenant, body)

    def edit_contact(self, tenant, phonebook_id, contact_uuid, contact_info):
        return self._contact_crud.edit(tenant, phonebook_id, contact_uuid, contact_info)

    def edit_phonebook(self, tenant, phonebook_id, phonebook_info):
        body, errors = _PhonebookSchema().load(phonebook_info)
        if errors:
            raise InvalidPhonebookException(errors)
        return self._phonebook_crud.edit(tenant, phonebook_id, body)

    def delete_contact(self, tenant, phonebook_id, contact_uuid):
        return self._contact_crud.delete(tenant, phonebook_id, contact_uuid)

    def delete_phonebook(self, tenant, phonebook_id):
        return self._phonebook_crud.delete(tenant, phonebook_id)

    def get_contact(self, tenant, phonebook_id, contact_uuid):
        return self._contact_crud.get(tenant, phonebook_id, contact_uuid)

    def get_phonebook(self, tenant, phonebook_id):
        return self._phonebook_crud.get(tenant, phonebook_id)
