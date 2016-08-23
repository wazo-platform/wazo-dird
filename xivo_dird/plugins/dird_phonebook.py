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

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from xivo_dird import BaseSourcePlugin, make_result_class, database

logger = logging.getLogger(__name__)


class PhonebookPlugin(BaseSourcePlugin):

    def load(self, config):
        logger.debug('Loading phonebook source')
        Session = scoped_session(sessionmaker())
        unique_column = 'id'
        source_name = config['config']['name']
        format_columns = config['config'].get(self.FORMAT_COLUMNS, {})
        db_uri = config['config']['db_uri']
        searched_columns = config['config'].get(self.SEARCHED_COLUMNS)
        first_matched_columns = config['config'].get(self.FIRST_MATCHED_COLUMNS)
        tenant = config['config']['tenant']
        phonebook_id = config['config']['phonebook_id']
        engine = create_engine(db_uri)
        Session.configure(bind=engine)
        self._search_engine = database.PhonebookContactSearchEngine(
            Session, tenant, phonebook_id, searched_columns, first_matched_columns
        )
        self._SourceResult = make_result_class(source_name, unique_column, format_columns)

    def search(self, term, *args, **kwargs):
        logger.debug('Searching phonebook contact with %s', term)
        matching_contacts = self._search_engine.find_contacts(term)
        return self.format_contacts(matching_contacts)

    def first_match(self, term, *args, **kwargs):
        logger.debug('First matching phonebook contacts with %s', term)
        matching_contact = self._search_engine.find_first_contact(term)
        for contact in self.format_contacts([matching_contact]):
            return contact

    def list(self, source_entry_ids, *args, **kwargs):
        logger.debug('Listing phonebook contacts')
        matching_contacts = self._search_engine.list_contacts(source_entry_ids)
        return self.format_contacts(matching_contacts)

    def format_contacts(self, contacts):
        return [self._SourceResult(c) for c in contacts]
