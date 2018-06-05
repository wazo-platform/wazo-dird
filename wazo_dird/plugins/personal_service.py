# -*- coding: utf-8 -*-
# Copyright 2015-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from wazo_dird import BaseServicePlugin
from wazo_dird import database, exception

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

    NoSuchContact = exception.NoSuchContact
    DuplicatedContactException = exception.DuplicatedContactException

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
        existing_contact_uuids = set([contact['id'] for contact in self._crud.list_personal_contacts()])

        for contact_info in contact_infos:
            try:
                if None in contact_info.keys():
                    raise PersonalImportError('too many fields')
                if None in contact_info.values():
                    raise PersonalImportError('missing fields')

                self.validate_contact(contact_info, existing_contact_uuids)
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
    def validate_contact(contact_infos, existing_contact_uuids=None):
        errors = []

        if any(not hasattr(key, 'encode') for key in contact_infos):
            errors.append('all keys must be strings')

        if any(not hasattr(value, 'encode') for value in contact_infos.itervalues()):
            errors.append('all values must be strings')

        if '' in contact_infos:
            errors.append('"" is a forbidden in keys')

        if errors:
            raise _PersonalService.InvalidPersonalContact(errors)

        if existing_contact_uuids:
            uuid = contact_infos.get('id', contact_infos.get('uuid'))
            if uuid and uuid in existing_contact_uuids:
                raise PersonalImportError('contact "{}" already exist'.format(uuid))


class DisabledPersonalSource(object):
    def list(self, _source_entry_ids, _token_infos):
        return []
