# -*- coding: utf-8 -*-
# Copyright 2015-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from xivo_dird import BaseSourcePlugin
from xivo_dird import make_result_class
from xivo_dird import database

logger = logging.getLogger(__name__)

Session = scoped_session(sessionmaker())


class PersonalBackend(BaseSourcePlugin):

    def load(self, config, search_engine=None):
        logger.debug('Loading personal source')

        unique_column = 'id'
        source_name = config['config']['name']
        format_columns = config['config'].get(self.FORMAT_COLUMNS, {})

        result_class = make_result_class(
            source_name,
            unique_column,
            format_columns,
            is_personal=True,
            is_deletable=True
        )
        self._SourceResult = lambda contact: result_class(self._remove_empty_values(contact))
        self._search_engine = search_engine or self._new_search_engine(config['config']['db_uri'],
                                                                       config['config'].get(self.SEARCHED_COLUMNS),
                                                                       config['config'].get(self.FIRST_MATCHED_COLUMNS))

    def search(self, term, args=None):
        logger.debug('Searching personal contacts with %s', term)
        user_uuid = args['xivo_user_uuid']
        matching_contacts = self._search_engine.find_personal_contacts(user_uuid, term)
        return self.format_contacts(matching_contacts)

    def first_match(self, term, args=None):
        logger.debug('First matching personal contacts with %s', term)
        user_uuid = args['xivo_user_uuid']
        matching_contacts = self._search_engine.find_first_personal_contact(user_uuid, term)
        for contact in self.format_contacts(matching_contacts):
            return contact

    def list(self, source_entry_ids, args):
        logger.debug('Listing personal contacts')
        user_uuid = args['token_infos']['xivo_user_uuid']
        matching_contacts = self._search_engine.list_personal_contacts(user_uuid, source_entry_ids)
        return self.format_contacts(matching_contacts)

    def format_contacts(self, contacts):
        return [self._SourceResult(contact) for contact in contacts]

    def _new_search_engine(self, db_uri, searched_columns, first_match_columns):
        engine = create_engine(db_uri)
        Session.configure(bind=engine)
        return database.PersonalContactSearchEngine(Session,
                                                    searched_columns,
                                                    first_match_columns)

    @staticmethod
    def _remove_empty_values(dict_):
        return {attribute: value for attribute, value in dict_.iteritems() if value}
