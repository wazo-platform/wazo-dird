# -*- coding: utf-8 -*-

# Copyright 2016-2017 The Wazo Authors  (see the AUTHORS file)
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
from collections import defaultdict

from sqlalchemy.sql.functions import ReturnTypeFromArgs
from sqlalchemy import and_, distinct, event, exc, func, or_
from sqlalchemy.pool import Pool
from sqlalchemy.orm.session import make_transient

from xivo_dird.core.database import (Contact,
                                     ContactFields,
                                     Favorite,
                                     Phonebook,
                                     Source,
                                     Tenant,
                                     User)
from xivo_dird.core.exception import (DatabaseServiceUnavailable,
                                      DuplicatedContactException,
                                      DuplicatedFavoriteException,
                                      DuplicatedPhonebookException,
                                      NoSuchContact,
                                      NoSuchFavorite,
                                      NoSuchPhonebook)


# http://stackoverflow.com/questions/34828113/flask-sqlalchemy-losing-connection-after-restarting-of-db-server
@event.listens_for(Pool, "checkout")
def ping_connection(dbapi_connection, connection_record, connection_proxy):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SELECT 1")
    except exc.OperationalError:
        # optional - dispose the whole pool
        # instead of invalidating one at a time
        # connection_proxy._pool.dispose()

        # raise DisconnectionError - pool will try
        # connecting again up to three times before raising.
        raise exc.DisconnectionError()
    cursor.close()


class unaccent(ReturnTypeFromArgs):
    pass


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


def delete_user(session, xivo_user_uuid):
    session.query(User).filter(User.xivo_user_uuid == xivo_user_uuid).delete()


class _BaseDAO(object):

    def __init__(self, Session):
        self._Session = Session

    def flush_or_raise(self, session, Exception_, *args, **kwargs):
        try:
            session.flush()
        except exc.IntegrityError:
            session.rollback()
            raise Exception_(*args, **kwargs)

    @contextmanager
    def new_session(self):
        session = self._Session()
        try:
            yield session
            session.commit()
        except exc.OperationalError:
            session.rollback()
            raise DatabaseServiceUnavailable()
        except:
            session.rollback()
            raise
        finally:
            self._Session.remove()

    def _get_dird_user(self, session, xivo_user_uuid):
        user = session.query(User).filter(User.xivo_user_uuid == xivo_user_uuid).first()
        if not user:
            user = User(xivo_user_uuid=xivo_user_uuid)
            session.add(user)
            session.flush()

        return user


class PhonebookContactCRUD(_BaseDAO):

    def count(self, tenant, phonebook_id, search=None):
        with self.new_session() as s:
            query = func.count(distinct(ContactFields.contact_uuid))
            return self._list_contacts(s, query, tenant, phonebook_id, search).scalar()

    def create(self, tenant, phonebook_id, contact_body):
        with self.new_session() as s:
            self._assert_tenant_owns_phonebook(s, tenant, phonebook_id)
            return self._create_one(s, tenant, phonebook_id, contact_body)

    def create_many(self, tenant, phonebook_id, body):
        created = []
        errors = []
        with self.new_session() as s:
            self._assert_tenant_owns_phonebook(s, tenant, phonebook_id)
            for contact_body in body:
                try:
                    contact = self._create_one(s, tenant, phonebook_id, contact_body)
                    created.append(contact)
                except Exception:
                    errors.append(contact_body)
        return created, errors

    def _create_one(self, session, tenant, phonebook_id, contact_body):
        hash_ = compute_contact_hash(contact_body)
        contact = Contact(phonebook_id=phonebook_id, hash=hash_)
        session.add(contact)
        self.flush_or_raise(session, DuplicatedContactException)
        self._add_field_to_contact(session, contact.uuid, contact_body)
        return contact_body

    def delete(self, tenant, phonebook_id, contact_id):
        with self.new_session() as s:
            contact = self._get_contact(s, tenant, phonebook_id, contact_id)
            s.delete(contact)

    def edit(self, tenant, phonebook_id, contact_uuid, contact_body):
        hash_ = compute_contact_hash(contact_body)
        with self.new_session() as s:
            contact = self._get_contact(s, tenant, phonebook_id, contact_uuid)
            contact.hash = hash_
            self.flush_or_raise(s, DuplicatedContactException)
            s.query(ContactFields).filter(ContactFields.contact_uuid == contact_uuid).delete()
            self._add_field_to_contact(s, contact.uuid, contact_body)

        return contact_body

    def get(self, tenant, phonebook_id, contact_id):
        with self.new_session() as s:
            self._assert_tenant_owns_phonebook(s, tenant, phonebook_id)
            filter_ = self._new_contact_filter(phonebook_id, contact_id)
            fields = s.query(ContactFields).join(Contact).filter(filter_).all()
            if not fields:
                raise NoSuchContact(contact_id)

            return {field.name: field.value for field in fields}

    def list(self, tenant, phonebook_id, search=None):
        with self.new_session() as s:
            query = distinct(ContactFields.contact_uuid)
            matching_uuids = self._list_contacts(s, query, tenant, phonebook_id, search).all()
            if not matching_uuids:
                return []

            fields = s.query(ContactFields).filter(ContactFields.contact_uuid.in_(matching_uuids)).all()
            result = defaultdict(dict)
            for field in fields:
                result[field.contact_uuid][field.name] = field.value

        return result.values()

    def _add_field_to_contact(self, s, contact_uuid, contact_body):
        for name, value in contact_body.iteritems():
            s.add(ContactFields(name=name, value=value, contact_uuid=contact_uuid))
            s.add(ContactFields(name='id', value=contact_uuid, contact_uuid=contact_uuid))
        contact_body['id'] = contact_uuid

    def _assert_tenant_owns_phonebook(self, s, tenant, phonebook_id):
        # XXX: use a cache to avoid the query at each operation?
        filter_ = and_(Phonebook.id == phonebook_id, Tenant.name == tenant)
        if not s.query(Phonebook).join(Tenant).filter(filter_).first():
            raise NoSuchPhonebook(phonebook_id)

    def _get_contact(self, s, tenant, phonebook_id, contact_uuid):
        self._assert_tenant_owns_phonebook(s, tenant, phonebook_id)
        filter_ = self._new_contact_filter(phonebook_id, contact_uuid)
        contact = s.query(Contact).filter(filter_).first()
        if not contact:
            raise NoSuchContact(contact_uuid)
        return contact

    def _list_contacts(self, s, query, tenant, phonebook_id, search):
        self._assert_tenant_owns_phonebook(s, tenant, phonebook_id)
        base_filter = Contact.phonebook_id == phonebook_id
        search_filter = ContactFields.value.ilike(u'%{}%'.format(search)) if search else True
        return s.query(query).join(Contact).filter(and_(base_filter, search_filter))

    def _new_contact_filter(self, phonebook_id, contact_uuid):
        return and_(Contact.uuid == contact_uuid, Contact.phonebook_id == phonebook_id)


class PhonebookCRUD(_BaseDAO):

    _default_sort_order = 'name'
    _default_sort_direction = 'asc'

    def count(self, tenant, search=None):
        with self.new_session() as s:
            return self._count_by_tenant(s, tenant, search)

    def create(self, tenant, phonebook_body):
        with self.new_session() as s:
            tenant = self._get_or_create_tenant(s, tenant)
            phonebook = Phonebook(tenant_id=tenant.id,
                                  **phonebook_body)
            s.add(phonebook)
            self.flush_or_raise(s, DuplicatedPhonebookException)

            return self._phonebook_to_dict(phonebook)

    def delete(self, tenant, phonebook_id):
        with self.new_session() as s:
            phonebook = self._get_by_tenant_and_id(s, tenant, phonebook_id)
            s.delete(phonebook)

    def edit(self, tenant, phonebook_id, phonebook_body):
        with self.new_session() as s:
            phonebook = self._get_by_tenant_and_id(s, tenant, phonebook_id)
            for attribute_name, value in phonebook_body.iteritems():
                if not hasattr(phonebook, attribute_name):
                    raise TypeError('{} has no attribute {}'.format(phonebook.__class__.__name__,
                                                                    attribute_name))
                setattr(phonebook, attribute_name, value)
            return self._phonebook_to_dict(phonebook)

    def get(self, tenant, phonebook_id):
        with self.new_session() as s:
            phonebook = self._get_by_tenant_and_id(s, tenant, phonebook_id)
            return self._phonebook_to_dict(phonebook)

    def list(self, tenant, order=None, direction=None, limit=None, offset=None, search=None):
        with self.new_session() as s:
            phonebooks = self._get_by_tenant(s, tenant, order, direction, limit, offset, search)
            return [self._phonebook_to_dict(phonebook) for phonebook in phonebooks]

    def _count_by_tenant(self, s, tenant, search):
        filter_ = self._new_tenant_filter(s, tenant, search)
        return s.query(func.count(Phonebook.id)).filter(filter_).scalar()

    def _get_by_tenant(self, s, tenant, order, direction, limit, offset, search):
        order_by_column_name = order or self._default_sort_order
        try:
            order_by_column = getattr(Phonebook, order_by_column_name)
        except AttributeError:
            raise TypeError('{} has no attribute {}'.format(Phonebook.__class__.__name__,
                                                            order_by_column_name))
        direction = direction or self._default_sort_direction
        order_by_column_and_direction = getattr(order_by_column, direction)()
        filter_ = self._new_tenant_filter(s, tenant, search)
        return s.query(Phonebook).filter(filter_).order_by(
            order_by_column_and_direction).limit(limit).offset(offset).all()

    def _get_by_tenant_and_id(self, s, tenant, phonebook_id):
        filter_ = self._new_filter_by_tenant_and_id(s, tenant, phonebook_id)
        phonebook = s.query(Phonebook).filter(filter_).scalar()
        if not phonebook:
            raise NoSuchPhonebook(phonebook_id)

        return phonebook

    def _new_tenant_filter(self, s, tenant, search):
        tenant = self._get_tenant(s, tenant)
        if not tenant:
            return False

        if not search:
            return Phonebook.tenant_id == tenant.id
        else:
            pattern = u'%{}%'.format(search)
            return and_(Phonebook.tenant_id == tenant.id,
                        or_(Phonebook.name.ilike(pattern),
                            Phonebook.description.ilike(pattern)))

    def _new_filter_by_tenant_and_id(self, s, tenant, phonebook_id):
        tenant = self._get_tenant(s, tenant)
        if not tenant:
            return False

        return and_(Phonebook.id == phonebook_id,
                    Phonebook.tenant_id == tenant.id)

    def _get_tenant(self, s, name):
        return s.query(Tenant).filter(Tenant.name == name).first()

    def _get_or_create_tenant(self, s, name):
        tenant = self._get_tenant(s, name)
        if not tenant:
            tenant = Tenant(name=name)
            s.add(tenant)
            s.flush()

        return tenant

    @staticmethod
    def _phonebook_to_dict(phonebook):
        return {'id': phonebook.id,
                'name': phonebook.name,
                'description': phonebook.description}


class FavoriteCRUD(_BaseDAO):

    def create(self, xivo_user_uuid, source_name, contact_id):
        with self.new_session() as s:
            user = self._get_dird_user(s, xivo_user_uuid)
            source = self._get_source(s, source_name)
            favorite = Favorite(source_id=source.id,
                                contact_id=contact_id,
                                user_uuid=user.xivo_user_uuid)
            s.add(favorite)
            self.flush_or_raise(s, DuplicatedFavoriteException)
            make_transient(favorite)
            return favorite

    def delete(self, xivo_user_uuid, source_name, contact_id):
        with self.new_session() as s:
            source_id = s.query(Source.id).filter(Source.name == source_name).scalar()
            filter_ = and_(Favorite.contact_id == contact_id,
                           Favorite.user_uuid == xivo_user_uuid,
                           Favorite.source_id == source_id)
            deleted = s.query(Favorite).filter(filter_).delete(synchronize_session=False)

            s.commit()

        if not deleted:
            raise NoSuchFavorite((source_name, contact_id))

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

        raise NoSuchContact(contact_uuid)

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
            raise NoSuchContact(contact_uuid)

    def _delete_personal_contacts_with_filter(self, session, filter_):
        contacts = session.query(Contact).join(ContactFields).join(User).filter(filter_).all()
        deleted = 0
        for contact in contacts:
            session.delete(contact)
            deleted += 1
        return deleted


class PhonebookContactSearchEngine(_BaseDAO):

    def __init__(self, Session, tenant, phonebook_id, searched_columns=None, first_match_columns=None):
        super(PhonebookContactSearchEngine, self).__init__(Session)
        self._searched_columns = searched_columns
        self._first_match_columns = first_match_columns
        self._tenant = tenant
        self._phonebook_id = phonebook_id

    def find_contacts(self, term):
        pattern = u'%{}%'.format(term)
        filter_ = self._new_search_filter(pattern, self._searched_columns)
        with self.new_session() as s:
            return self._find_contacts_with_filter(s, filter_)

    def find_first_contact(self, term):
        filter_ = self._new_search_filter(term, self._first_match_columns)
        with self.new_session() as s:
            for contact in self._find_contacts_with_filter(s, filter_, limit=1):
                return contact

    def list_contacts(self, contact_uuids):
        filter_ = self._new_list_filter(contact_uuids)
        with self.new_session() as s:
            return self._find_contacts_with_filter(s, filter_)

    def _find_contacts_with_filter(self, s, filter_, limit=None):
        query = (s.query(distinct(ContactFields.contact_uuid))
                 .join(Contact)
                 .join(Phonebook)
                 .join(Tenant)
                 .filter(and_(filter_,
                              Phonebook.id == self._phonebook_id,
                              Tenant.name == self._tenant)))

        if limit:
            query = query.limit(limit)

        uuids = [uuid for (uuid,) in query.all()]

        return _list_contacts_by_uuid(s, uuids)

    def _new_list_filter(self, contact_uuids):
        if not contact_uuids:
            return False

        return ContactFields.contact_uuid.in_(contact_uuids)

    def _new_search_filter(self, pattern, columns):
        if not columns:
            return False

        return and_(ContactFields.value.ilike(pattern),
                    ContactFields.name.in_(columns))


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
