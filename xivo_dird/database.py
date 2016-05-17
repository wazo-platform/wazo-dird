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

from unidecode import unidecode
from contextlib import contextmanager

from sqlalchemy.sql.functions import ReturnTypeFromArgs
from sqlalchemy import and_, Column, distinct, ForeignKey, Integer, schema, String, text, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class unaccent(ReturnTypeFromArgs):
    pass


class NoSuchFavorite(ValueError):

    def __init__(self, contact_id):
        message = "No such favorite: {}".format(contact_id)
        super(NoSuchFavorite, self).__init__(message)


class NoSuchPersonalContact(ValueError):

    def __init__(self, contact_id):
        message = "No such personal contact: {}".format(contact_id)
        super(NoSuchPersonalContact, self).__init__(message)


class DuplicatedContactException(Exception):
    pass


class User(Base):

    __tablename__ = 'dird_user'

    xivo_user_uuid = Column(String(38), primary_key=True)


class Contact(Base):

    __tablename__ = 'dird_contact'
    __table_args__ = (schema.UniqueConstraint('user_uuid', 'hash'),)

    uuid = Column(String(38), server_default=text('uuid_generate_v4()'), primary_key=True)
    user_uuid = Column(String(38), ForeignKey('dird_user.xivo_user_uuid', ondelete='CASCADE'), nullable=False)
    hash = Column(String(40), nullable=False)


class ContactFields(Base):

    __tablename__ = 'dird_contact_fields'

    id = Column(Integer(), primary_key=True)
    name = Column(Text(), nullable=False, index=True)
    value = Column(Text(), index=True)
    contact_uuid = Column(String(38), ForeignKey('dird_contact.uuid', ondelete='CASCADE'), nullable=False)


class Favorite(Base):

    __tablename__ = 'dird_favorite'

    source_id = Column(Integer(), ForeignKey('dird_source.id', ondelete='CASCADE'), primary_key=True)
    contact_id = Column(Text(), primary_key=True)
    user_uuid = Column(String(38), ForeignKey('dird_user.xivo_user_uuid', ondelete='CASCADE'), primary_key=True)


class Source(Base):

    __tablename__ = 'dird_source'

    id = Column(Integer(), primary_key=True)
    name = Column(Text(), nullable=False, unique=True)


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


class _BaseDAO(object):

    def __init__(self, Session):
        self._Session = Session

    @contextmanager
    def new_session(self):
        session = self._Session()
        yield session
        session.commit()

    def _get_dird_user(self, session, xivo_user_uuid):
        user = session.query(User).filter(User.xivo_user_uuid == xivo_user_uuid).first()
        if not user:
            user = User(xivo_user_uuid=xivo_user_uuid)
            session.add(user)
            session.flush()

        return user


class FavoriteCRUD(_BaseDAO):

    def create(self, xivo_user_uuid, source_name, contact_id):
        with self.new_session() as s:
            user = self._get_dird_user(s, xivo_user_uuid)
            source = self._get_source(s, source_name)
            favorite = Favorite(source_id=source.id,
                                contact_id=contact_id,
                                user_uuid=user.xivo_user_uuid)
            s.add(favorite)
            s.commit()
            return favorite

    def delete(self, xivo_user_uuid, contact_id):
        with self.new_session() as s:
            deleted = s.query(Favorite).filter(and_(Favorite.contact_id == contact_id,
                                                    Favorite.user_uuid == xivo_user_uuid)).delete(synchronize_session=False)

            s.commit()

        if not deleted:
            raise NoSuchFavorite(contact_id)

    def get(self, xivo_user_uuid):
        with self.new_session() as s:
            favorites = s.query(Favorite.contact_id, Source.name).join(Source).filter(Favorite.user_uuid == xivo_user_uuid)
            return [(f.name, f.contact_id) for f in favorites.all()]

    def _get_source(self, session, source_name):
        source = session.query(Source).filter(Source.name == source_name).first()
        if not source:
            source = Source(name=source_name)
            session.add(source)
            session.flush()

        return source


class PersonalContactCRUD(_BaseDAO):

    def list_personal_contacts(self, xivo_user_uuid):
        with self.new_session() as s:
            query = s.query(distinct(Contact.uuid)).filter(Contact.user_uuid == xivo_user_uuid)
            contact_uuids = [uuid for (uuid,) in query.all()]
            return _list_contacts_by_uuid(s, contact_uuids)

    def create_personal_contact(self, xivo_user_uuid, contact_info):
        with self.new_session() as s:
            for contact in self._create_personal_contacts(s, xivo_user_uuid, [contact_info], fail_on_duplicate=True):
                return contact

    def create_personal_contacts(self, xivo_user_uuid, contact_infos):
        with self.new_session() as s:
            return self._create_personal_contacts(s, xivo_user_uuid, contact_infos)

    def _create_personal_contacts(self, session, xivo_user_uuid, contact_infos, fail_on_duplicate=False):
        hash_and_contact = {compute_contact_hash(c): c for c in contact_infos}
        user = self._get_dird_user(session, xivo_user_uuid)
        existing_hashes_and_id = self._find_existing_contact_by_hash(session, xivo_user_uuid, hash_and_contact.keys())
        all_hashes = set(hash_and_contact.keys())
        to_add = all_hashes - set(existing_hashes_and_id.keys())
        existing = all_hashes - to_add
        if existing and fail_on_duplicate:
            raise DuplicatedContactException()

        for hash_ in to_add:
            contact_info = hash_and_contact[hash_]
            contact_args = {'user_uuid': user.xivo_user_uuid,
                            'hash': hash_}
            contact_uuid = contact_info.get('id')
            if contact_uuid:
                contact_args['uuid'] = contact_uuid
            contact = Contact(**contact_args)
            session.add(contact)
            session.flush()
            for name, value in contact_info.iteritems():
                session.add(ContactFields(name=name, value=value, contact_uuid=contact.uuid))
                session.add(ContactFields(name='id', value=contact.uuid, contact_uuid=contact.uuid))
            contact_info['id'] = contact.uuid

        for hash_ in existing:
            contact_info = hash_and_contact[hash_]
            contact_info['id'] = existing_hashes_and_id[hash_]

        return contact_infos

    def _find_existing_contact_by_hash(self, session, xivo_user_uuid, hashes):
        if not hashes:
            return {}

        filter_ = and_(Contact.user_uuid == xivo_user_uuid,
                       Contact.hash.in_(hashes))
        pairs = session.query(Contact.hash, Contact.uuid).filter(filter_)
        return {p.hash: p.uuid for p in pairs.all()}

    def edit_personal_contact(self, xivo_user_uuid, contact_id, contact_info):
        with self.new_session() as s:
            self._delete_personal_contact(s, xivo_user_uuid, contact_id)
            hash_ = compute_contact_hash(contact_info)
            if self._find_existing_contact_by_hash(s, xivo_user_uuid, [hash_]):
                s.rollback()
                raise DuplicatedContactException()
            contact_info['id'] = contact_id
            for contact in self._create_personal_contacts(s, xivo_user_uuid, [contact_info]):
                return contact

    def get_personal_contact(self, xivo_user_uuid, contact_uuid):
        with self.new_session() as s:
            filter_ = and_(User.xivo_user_uuid == xivo_user_uuid,
                           ContactFields.contact_uuid == contact_uuid)
            contact_uuids = (s.query(distinct(ContactFields.contact_uuid))
                             .join(Contact)
                             .join(User)
                             .filter(filter_))

            for contact in _list_contacts_by_uuid(s, contact_uuids):
                return contact

        raise NoSuchPersonalContact(contact_uuid)

    def delete_all_personal_contacts(self, xivo_user_uuid):
        with self.new_session() as s:
            filter_ = User.xivo_user_uuid == xivo_user_uuid
            return self._delete_personal_contacts_with_filter(s, filter_)

    def delete_personal_contact(self, xivo_user_uuid, contact_uuid):
        with self.new_session() as s:
            self._delete_personal_contact(s, xivo_user_uuid, contact_uuid)

    def _delete_personal_contact(self, session, xivo_user_uuid, contact_uuid):
        filter_ = and_(User.xivo_user_uuid == xivo_user_uuid,
                       ContactFields.contact_uuid == contact_uuid)
        nb_deleted = self._delete_personal_contacts_with_filter(session, filter_)
        if nb_deleted == 0:
            raise NoSuchPersonalContact(contact_uuid)

    def _delete_personal_contacts_with_filter(self, session, filter_):
        contacts = session.query(Contact).join(ContactFields).join(User).filter(filter_).all()
        deleted = 0
        for contact in contacts:
            session.delete(contact)
            deleted += 1
        return deleted


class PersonalContactSearchEngine(_BaseDAO):

    def __init__(self, Session, searched_columns=None, first_match_columns=None):
        super(PersonalContactSearchEngine, self).__init__(Session)
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

        with self.new_session() as s:
            base_query = (s.query(distinct(ContactFields.contact_uuid))
                          .join(Contact)
                          .join(User)
                          .filter(filter_))
            if limit:
                query = base_query.limit(limit)
            else:
                query = base_query

            uuids = [uuid for (uuid,) in query.all()]

            return _list_contacts_by_uuid(s, uuids)

    def _new_list_filter(self, xivo_user_uuid, uuids):
        if not uuids:
            return False

        return and_(User.xivo_user_uuid == xivo_user_uuid,
                    ContactFields.contact_uuid.in_(uuids))

    def _new_search_filter(self, xivo_user_uuid, term, columns):
        if not columns:
            return False

        pattern = u'%{}%'.format(unidecode(term))
        return and_(User.xivo_user_uuid == xivo_user_uuid,
                    unaccent(ContactFields.value).ilike(pattern),
                    ContactFields.name.in_(columns))

    def _new_strict_filter(self, xivo_user_uuid, term, columns):
        if not columns:
            return False

        return and_(User.xivo_user_uuid == xivo_user_uuid,
                    unaccent(ContactFields.value) == unidecode(term),
                    ContactFields.name.in_(columns))

    def _new_user_contacts_filter(self, xivo_user_uuid):
        return User.xivo_user_uuid == xivo_user_uuid
