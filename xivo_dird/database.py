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

    def __init__(self, session):
        self._session = session

    def find_personal_contacts(self, xivo_user_uuid, term):
        pattern = '%{}%'.format(term)
        query = (self._session.query(ContactFields.contact_uuid)
                 .join(Contact)
                 .join(User)
                 .filter(and_(User.xivo_user_uuid == xivo_user_uuid,
                              ContactFields.value.ilike(pattern))))
        matching_contacts = query.all()

        if not matching_contacts:
            return []

        contact_fields = self._session.query(ContactFields).filter(ContactFields.contact_uuid.in_(matching_contacts)).all()
        result = {}
        for contact_field in contact_fields:
            uuid = contact_field.contact_uuid
            if uuid not in result:
                result[uuid] = {'id': uuid}
            result[uuid][contact_field.name] = contact_field.value

        return result.values()
