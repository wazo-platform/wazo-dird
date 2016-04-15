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

from sqlalchemy import and_, Column, ForeignKey, Integer, String, text, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):

    __tablename__ = 'dird_user'

    xivo_user_uuid = Column(String(38), nullable=False, primary_key=True)


class Contact(Base):

    __tablename__ = 'dird_contact'

    uuid = Column(String(38), server_default=text('uuid_generate_v4()'), primary_key=True)
    user_uuid = Column(String(38), ForeignKey('dird_user.xivo_user_uuid', ondelete='CASCADE'), nullable=False)


class ContactFields(Base):

    __tablename__ = 'dird_contact_fields'

    id = Column(Integer(), primary_key=True)
    name = Column(String(20), nullable=False)
    value = Column(Text())
    contact_uuid = Column(String(38), ForeignKey('dird_contact.uuid', ondelete='CASCADE'), nullable=False)


class PersonalContactSearchEngine(object):

    def __init__(self, Session, unique_column='id', searched_columns=None):
        self._Session = Session
        self._unique_column = unique_column
        self._searched_columns = searched_columns or []

    def find_personal_contacts(self, xivo_user_uuid, term):
        query = (self._session.query(ContactFields.contact_uuid)
                 .join(Contact)
                 .join(User)
                 .filter(self._new_search_filter(xivo_user_uuid, term)))
        matching_contacts = query.all()

        if not matching_contacts:
            return []

        contact_fields = self._session.query(ContactFields).filter(ContactFields.contact_uuid.in_(matching_contacts)).all()
        result = {}
        for contact_field in contact_fields:
            uuid = contact_field.contact_uuid
            if uuid not in result:
                result[uuid] = {self._unique_column: uuid}
            result[uuid][contact_field.name] = contact_field.value

        return result.values()

    def _new_search_filter(self, xivo_user_uuid, term):
        if not self._searched_columns:
            return False

        pattern = '%{}%'.format(term)
        return and_(User.xivo_user_uuid == xivo_user_uuid,
                    ContactFields.value.ilike(pattern),
                    ContactFields.name.in_(self._searched_columns))

    @property
    def _session(self):
        return self._Session()
