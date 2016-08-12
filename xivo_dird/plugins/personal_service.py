# -*- coding: utf-8 -*-

# Copyright (C) 2015-2016 Avencall
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

from xivo_dird import BaseServicePlugin
from xivo_dird import database

logger = logging.getLogger(__name__)


UNIQUE_COLUMN = 'id'


class PersonalImportError(ValueError):
    pass


class PersonalServicePlugin(BaseServicePlugin):

    def load(self, args):
        try:
            config = args['config']
            sources = args['sources']
        except KeyError:
            msg = ('%s should be loaded with "config" and "sources" but received: %s'
                   % (self.__class__.__name__, ','.join(args.keys())))
            raise ValueError(msg)

        crud = self._new_personal_contact_crud(config['db_uri'])

        return _PersonalService(config, sources, crud)

    def _new_personal_contact_crud(self, db_uri):
        self._Session = scoped_session(sessionmaker())
        engine = create_engine(db_uri)
        self._Session.configure(bind=engine)
        return database.PersonalContactCRUD(self._Session)


class _PersonalService(object):

    NoSuchContact = database.NoSuchContact
    DuplicatedContactException = database.DuplicatedContactException

    class InvalidPersonalContact(ValueError):
        def __init__(self, errors):
            message = "Invalid personal contact: {}".format(errors)
            ValueError.__init__(self, message)
            self.errors = errors

    def __init__(self, config, sources, crud):
        self._crud = crud
        self._config = config
        self._source = next((source for source in sources.itervalues() if source.backend == 'personal'),
                            DisabledPersonalSource())

    def create_contact(self, contact_infos, token_infos):
        self.validate_contact(contact_infos)
        return self._crud.create_personal_contact(token_infos['xivo_user_uuid'], contact_infos)

    def create_contacts(self, contact_infos, token_infos):
        errors = []
        to_add = []
        for contact_info in contact_infos:
            try:
                if None in contact_info.keys():
                    raise PersonalImportError('too many fields')
                if None in contact_info.values():
                    raise PersonalImportError('missing fields')

                self.validate_contact(contact_info)
                to_add.append(contact_info)
            except self.InvalidPersonalContact as e:
                errors.append({'errors': e.errors, 'line': contact_infos.line_num})
            except PersonalImportError as e:
                errors.append({'errors': [str(e)], 'line': contact_infos.line_num})

        return self._crud.create_personal_contacts(token_infos['xivo_user_uuid'], to_add), errors

    def get_contact(self, contact_id, token_infos):
        return self._crud.get_personal_contact(token_infos['xivo_user_uuid'], contact_id)

    def edit_contact(self, contact_id, contact_infos, token_infos):
        self.validate_contact(contact_infos)
        return self._crud.edit_personal_contact(token_infos['xivo_user_uuid'], contact_id, contact_infos)

    def remove_contact(self, contact_id, token_infos):
        self._crud.delete_personal_contact(token_infos['xivo_user_uuid'], contact_id)

    def purge_contacts(self, token_infos):
        self._crud.delete_all_personal_contacts(token_infos['xivo_user_uuid'])

    def list_contacts(self, token_infos):
        contacts = self._crud.list_personal_contacts(token_infos['xivo_user_uuid'])
        formatted_contacts = self._source.format_contacts(contacts)
        return formatted_contacts

    def list_contacts_raw(self, token_infos):
        return self._crud.list_personal_contacts(token_infos['xivo_user_uuid'])

    @staticmethod
    def validate_contact(contact_infos):
        errors = []

        if any(not hasattr(key, 'encode') for key in contact_infos):
            errors.append('all keys must be strings')

        if any(not hasattr(value, 'encode') for value in contact_infos.itervalues()):
            errors.append('all values must be strings')

        if '' in contact_infos:
            errors.append('"" is a forbidden in keys')

        if errors:
            raise _PersonalService.InvalidPersonalContact(errors)


class DisabledPersonalSource(object):
    def list(self, _source_entry_ids, _token_infos):
        return []
