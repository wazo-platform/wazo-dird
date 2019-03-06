# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unidecode import unidecode
from sqlalchemy import (
    and_,
    distinct,
    text,
)
from sqlalchemy.sql.functions import ReturnTypeFromArgs
from wazo_dird.exception import (
    DuplicatedContactException,
    NoSuchContact,
)
from .base import (
    BaseDAO,
    compute_contact_hash,
    list_contacts_by_uuid,
)
from .. import (
    Contact,
    ContactFields,
    User,
)


class unaccent(ReturnTypeFromArgs):
    pass


class PersonalContactSearchEngine(BaseDAO):

    def __init__(self, Session, searched_columns=None, first_match_columns=None):
        super().__init__(Session)
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

            return list_contacts_by_uuid(s, uuids)

    def _new_list_filter(self, xivo_user_uuid, uuids):
        if not uuids:
            return False

        return and_(User.xivo_user_uuid == xivo_user_uuid,
                    ContactFields.contact_uuid.in_(uuids))

    def _new_search_filter(self, xivo_user_uuid, term, columns):
        if not columns:
            return False

        pattern = '%{}%'.format(unidecode(term))
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
class PersonalContactCRUD(BaseDAO):

    def list_personal_contacts(self, xivo_user_uuid=None):
        filter_ = text('true')
        if xivo_user_uuid:
            filter_ = and_(filter_, Contact.user_uuid == xivo_user_uuid)

        with self.new_session() as s:
            query = s.query(distinct(Contact.uuid)).filter(filter_)
            contact_uuids = [uuid for (uuid,) in query.all()]
            return list_contacts_by_uuid(s, contact_uuids)

    def create_personal_contact(self, xivo_user_uuid, contact_info):
        with self.new_session() as s:
            for contact in self._create_personal_contacts(
                    s, xivo_user_uuid, [contact_info], fail_on_duplicate=True,
            ):
                return contact

    def create_personal_contacts(self, xivo_user_uuid, contact_infos):
        with self.new_session() as s:
            return self._create_personal_contacts(s, xivo_user_uuid, contact_infos)

    def _create_personal_contacts(
            self, session, xivo_user_uuid, contact_infos, fail_on_duplicate=False,
    ):
        hash_and_contact = {compute_contact_hash(c): c for c in contact_infos}
        user = self._get_dird_user(session, xivo_user_uuid)
        existing_hashes_and_id = self._find_existing_contact_by_hash(
            session, xivo_user_uuid, list(hash_and_contact.keys())
        )
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

            contact_info['id'] = contact.uuid
            for name, value in contact_info.items():
                session.add(ContactFields(name=name, value=value, contact_uuid=contact.uuid))

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

            for contact in list_contacts_by_uuid(s, contact_uuids):
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
