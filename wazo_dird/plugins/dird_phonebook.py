# -*- coding: utf-8 -*-
# Copyright 2016-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from wazo_dird import BaseSourcePlugin, make_result_class
from wazo_dird import database
from wazo_dird.exception import InvalidConfigError

logger = logging.getLogger(__name__)


class PhonebookPlugin(BaseSourcePlugin):

    def __init__(self, *args, **kwargs):
        self._crud = None
        self._tenant = None
        self._source_name = None
        super(PhonebookPlugin, self).__init__(*args, **kwargs)

    def load(self, config):
        logger.debug('Loading phonebook source')
        Session = scoped_session(sessionmaker())
        unique_column = 'id'
        self._source_name = config['config']['name']
        format_columns = config['config'].get(self.FORMAT_COLUMNS, {})
        db_uri = config['config']['db_uri']
        searched_columns = config['config'].get(self.SEARCHED_COLUMNS)
        first_matched_columns = config['config'].get(self.FIRST_MATCHED_COLUMNS)
        self._tenant = config['config']['tenant']
        engine = create_engine(db_uri)
        Session.configure(bind=engine)
        self._crud = database.PhonebookCRUD(Session)

        phonebook_id = self._get_phonebook_id(config['config'])

        self._search_engine = database.PhonebookContactSearchEngine(
            Session, self._tenant, phonebook_id, searched_columns, first_matched_columns
        )
        self._SourceResult = make_result_class(self._source_name, unique_column, format_columns)

    def search(self, term, *args, **kwargs):
        logger.debug('Searching phonebook contact with %s', term)
        matching_contacts = self._search_engine.find_contacts(term)
        return self.format_contacts(matching_contacts)

    def first_match(self, term, *args, **kwargs):
        logger.debug('First matching phonebook contacts with %s', term)
        matching_contact = self._search_engine.find_first_contact(term)
        if not matching_contact:
            logger.debug('Found no matching contact.')
            return None

        for contact in self.format_contacts([matching_contact]):
            logger.debug('Found one matching contact.')
            return contact

    def list(self, source_entry_ids, *args, **kwargs):
        logger.debug('Listing phonebook contacts')
        matching_contacts = self._search_engine.list_contacts(source_entry_ids)
        return self.format_contacts(matching_contacts)

    def format_contacts(self, contacts):
        return [self._SourceResult(c) for c in contacts]

    def _get_phonebook_id(self, config):
        if 'phonebook_id' in config:
            return config['phonebook_id']

        phonebook_name = config['phonebook_name']
        phonebooks = self._crud.list(self._tenant, search=phonebook_name)
        for phonebook in phonebooks:
            if phonebook['name'] == phonebook_name:
                return phonebook['id']

        raise InvalidConfigError('sources/{}/phonebook_name'.format(self._source_name),
                                 'unknown phonebook {}'.format(phonebook_name))
