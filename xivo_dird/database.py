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

import hashlib
import json

from sqlalchemy import and_, Column, distinct, ForeignKey, Integer, schema, String, text, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError

Base = declarative_base()


class NoSuchPersonalContact(ValueError):
    def __init__(self, contact_id):
        message = "No such personal contact: {}".format(contact_id)
        ValueError.__init__(self, message)


class DuplicatePersonalContact(Exception):
    pass


class User(Base):

    __tablename__ = 'dird_user'

    xivo_user_uuid = Column(String(38), nullable=False, primary_key=True)


class Contact(Base):

    __tablename__ = 'dird_contact'
    __table_args__ = (schema.UniqueConstraint('user_uuid', 'hash'),)

    uuid = Column(String(38), server_default=text('uuid_generate_v4()'), primary_key=True)
    user_uuid = Column(String(38), ForeignKey('dird_user.xivo_user_uuid', ondelete='CASCADE'), nullable=False)
    hash = Column(String(40), nullable=False)


class ContactFields(Base):

    __tablename__ = 'dird_contact_fields'

    id = Column(Integer(), primary_key=True)
    name = Column(String(20), nullable=False)
    value = Column(Text())
    contact_uuid = Column(String(38), ForeignKey('dird_contact.uuid', ondelete='CASCADE'), nullable=False)


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


def compute_contact_hash(contact_info):
    d = dict(contact_info)
    d.pop('id', None)
    string_representation = json.dumps(d, sort_keys=True)
    return hashlib.sha1(string_representation).hexdigest()


class PersonalContactCRUD(object):

    def __init__(self, Session):
        self._Session = Session

    def list_personal_contacts(self, xivo_user_uuid):
        session = self._new_session()
        query = session.query(distinct(Contact.uuid)).filter(Contact.user_uuid == xivo_user_uuid)
        contact_uuids = [uuid for (uuid,) in query.all()]
        return _list_contacts_by_uuid(session, contact_uuids)

    def create_personal_contact(self, xivo_user_uuid, contact_info):
        session = self._new_session()
        user = self._get_dird_user(session, xivo_user_uuid)
        hash_ = compute_contact_hash(contact_info)
        contact_args = {'user_uuid': user.xivo_user_uuid,
                        'hash': hash_}
        contact_uuid = contact_info.get('id')
        if contact_uuid:
            contact_args['uuid'] = contact_uuid
        contact = Contact(**contact_args)
        session.add(contact)
        try:
            session.flush()
        except IntegrityError:
            raise DuplicatePersonalContact()
        for name, value in contact_info.iteritems():
            session.add(ContactFields(name=name, value=value, contact_uuid=contact.uuid))
            session.add(ContactFields(name='id', value=contact.uuid, contact_uuid=contact.uuid))
            session.flush()
        contact_info['id'] = contact.uuid
        session.commit()
        return contact_info

    def edit_personal_contact(self, xivo_user_uuid, contact_id, contact_info):
        self.delete_personal_contact(xivo_user_uuid, contact_id)
        contact_info['id'] = contact_id
        return self.create_personal_contact(xivo_user_uuid, contact_info)

    def get_personal_contact(self, xivo_user_uuid, contact_uuid):
        session = self._new_session()
        filter_ = and_(User.xivo_user_uuid == xivo_user_uuid,
                       ContactFields.contact_uuid == contact_uuid)
        contact_uuids = (session.query(distinct(ContactFields.contact_uuid))
                         .join(Contact)
                         .join(User)
                         .filter(filter_))

        for contact in _list_contacts_by_uuid(session, contact_uuids):
            return contact

        raise NoSuchPersonalContact(contact_uuid)

    def delete_all_personal_contacts(self, xivo_user_uuid):
        filter_ = User.xivo_user_uuid == xivo_user_uuid
        return self._delete_personal_contacts_with_filter(filter_)

    def delete_personal_contact(self, xivo_user_uuid, contact_uuid):
        filter_ = and_(User.xivo_user_uuid == xivo_user_uuid,
                       ContactFields.contact_uuid == contact_uuid)
        return self._delete_personal_contacts_with_filter(filter_)

    def _delete_personal_contacts_with_filter(self, filter_):
        session = self._new_session()
        contacts = session.query(Contact).join(ContactFields).join(User).filter(filter_).all()
        for contact in contacts:
            session.delete(contact)
        session.commit()

    def _get_dird_user(self, session, xivo_user_uuid):
        user = session.query(User).filter(User.xivo_user_uuid == xivo_user_uuid).first()
        if user:
            return user
        else:
            user = User(xivo_user_uuid=xivo_user_uuid)
            session.add(user)
            session.flush()
            return user

    def _new_session(self):
        return self._Session()


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
