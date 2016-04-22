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

from sqlalchemy import and_, Column, distinct, ForeignKey, Integer, String, text, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class NoSuchPersonalContact(ValueError):
    def __init__(self, contact_id):
        message = "No such personal contact: {}".format(contact_id)
        ValueError.__init__(self, message)


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


def _get_dird_user(session, xivo_user_uuid):
    user = session.query(User).filter(User.xivo_user_uuid == xivo_user_uuid).first()
    if user:
        return user
    else:
        user = User(xivo_user_uuid=xivo_user_uuid)
        session.add(user)
        session.flush()
        return user


def _list_contacts_by_uuid(session, uuids):
    if not uuids:
        return []

    contact_fields = session.query(ContactFields).filter(ContactFields.contact_uuid.in_(uuids)).all()
    result = {}
    for contact_field in contact_fields:
        uuid = contact_field.contact_uuid
        if uuid not in result:
            result[uuid] = {'id': uuid}
        result[uuid][contact_field.name] = contact_field.value
    return result.values()


def list_personal_contacts(session, xivo_user_uuid):
    contact_uuids = [uuid for (uuid,) in session.query(distinct(Contact.uuid)).filter(Contact.user_uuid == xivo_user_uuid).all()]
    return _list_contacts_by_uuid(session, contact_uuids)


def create_personal_contact(session, xivo_user_uuid, contact_info):
    user = _get_dird_user(session, xivo_user_uuid)
    contact = Contact(user_uuid=user.xivo_user_uuid)
    session.add(contact)
    session.flush()
    for name, value in contact_info.iteritems():
        session.add(ContactFields(name=name, value=value, contact_uuid=contact.uuid))
    session.add(ContactFields(name='id', value=contact.uuid, contact_uuid=contact.uuid))
    session.commit()
    contact_info['id'] = contact.uuid
    return contact_info


def get_personal_contact(session, xivo_user_uuid, contact_uuid):
    filter_ = and_(User.xivo_user_uuid == xivo_user_uuid,
                   ContactFields.contact_uuid == contact_uuid)
    contact_uuids = (session.query(distinct(ContactFields.contact_uuid))
                     .join(Contact)
                     .join(User)
                     .filter(filter_))

    for contact in _list_contacts_by_uuid(session, contact_uuids):
        return contact

    raise NoSuchPersonalContact(contact_uuid)


def delete_personal_contact(session, xivo_user_uuid, contact_uuid):
    filter_ = and_(User.xivo_user_uuid == xivo_user_uuid,
                   ContactFields.contact_uuid == contact_uuid)
    contacts = session.query(Contact).join(ContactFields).join(User).filter(filter_).all()
    for contact in contacts:
        session.delete(contact)
    session.commit()


class PersonalContactSearchEngine(object):

    def __init__(self, Session, searched_columns=None, first_match_columns=None):
        self._Session = Session
        self._searched_columns = searched_columns or []
        self._first_match_columns = first_match_columns or []

    def find_first_personal_contact(self, xivo_user_uuid, term):
        filter_ = self._new_strict_filter(xivo_user_uuid, term, self._first_match_columns)
        return self._find_personal_contacts_with_filter(filter_, limit=1)

    def find_personal_contacts(self, xivo_user_uuid, term):
        filter_ = self._new_search_filter(xivo_user_uuid, term, self._searched_columns)
        return self._find_personal_contacts_with_filter(filter_)

    def list_personal_contacts(self, xivo_user_uuid, uuids=None):
        if uuids is None:
            filter_ = self._new_user_contacts_filter(xivo_user_uuid)
        else:
            filter_ = self._new_list_filter(xivo_user_uuid, uuids)
        return self._find_personal_contacts_with_filter(filter_)

    def _find_personal_contacts_with_filter(self, filter_, limit=None):
        if filter_ is False:
            return []

        base_query = (self._session.query(distinct(ContactFields.contact_uuid))
                      .join(Contact)
                      .join(User)
                      .filter(filter_))
        if limit:
            query = base_query.limit(limit)
        else:
            query = base_query

        uuids = [uuid for (uuid,) in query.all()]

        return _list_contacts_by_uuid(self._session, uuids)

    def _new_list_filter(self, xivo_user_uuid, uuids):
        if not uuids:
            return False

        return and_(User.xivo_user_uuid == xivo_user_uuid,
                    ContactFields.contact_uuid.in_(uuids))

    def _new_search_filter(self, xivo_user_uuid, term, columns):
        if not columns:
            return False

        pattern = '%{}%'.format(term)
        return and_(User.xivo_user_uuid == xivo_user_uuid,
                    ContactFields.value.ilike(pattern),
                    ContactFields.name.in_(columns))

    def _new_strict_filter(self, xivo_user_uuid, term, columns):
        if not columns:
            return False

        return and_(User.xivo_user_uuid == xivo_user_uuid,
                    ContactFields.value == term,
                    ContactFields.name.in_(columns))

    def _new_user_contacts_filter(self, xivo_user_uuid):
        return User.xivo_user_uuid == xivo_user_uuid

    @property
    def _session(self):
        return self._Session()
