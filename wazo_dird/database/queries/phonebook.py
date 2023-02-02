# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from collections import defaultdict
from sqlalchemy import and_, distinct, func, or_

from wazo_dird.exception import (
    DuplicatedContactException,
    DuplicatedPhonebookException,
    NoSuchContact,
    NoSuchPhonebook,
)

from .base import BaseDAO, compute_contact_hash, list_contacts_by_uuid
from .. import Contact, ContactFields, Phonebook, Tenant


class PhonebookContactSearchEngine(BaseDAO):
    def __init__(
        self,
        Session,
        tenant_uuid,
        phonebook_id,
        searched_columns=None,
        first_match_columns=None,
    ):
        super().__init__(Session)
        self._searched_columns = searched_columns
        self._first_match_columns = first_match_columns
        self._tenant_uuid = tenant_uuid
        self._phonebook_id = phonebook_id

    def find_contacts(self, term):
        pattern = '%{}%'.format(term)
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
        query = (
            s.query(distinct(ContactFields.contact_uuid))
            .join(Contact)
            .join(Phonebook)
            .filter(
                and_(
                    filter_,
                    Phonebook.id == self._phonebook_id,
                    Phonebook.tenant_uuid == self._tenant_uuid,
                )
            )
        )

        if limit:
            query = query.limit(limit)

        uuids = [uuid for (uuid,) in query.all()]

        return list_contacts_by_uuid(s, uuids)

    def _new_list_filter(self, contact_uuids):
        if not contact_uuids:
            return False

        return ContactFields.contact_uuid.in_(contact_uuids)

    def _new_search_filter(self, pattern, columns):
        if not columns:
            return False

        return and_(ContactFields.value.ilike(pattern), ContactFields.name.in_(columns))


class PhonebookContactCRUD(BaseDAO):
    def count(self, tenant_uuid, phonebook_id, search=None):
        with self.new_session() as s:
            phonebook = self._get_phonebook(s, tenant_uuid, phonebook_id)
            query = func.count(distinct(ContactFields.contact_uuid))
            return self._list_contacts(s, query, phonebook.id, search).scalar()

    def create(self, tenant_uuid, phonebook_id, contact_body):
        with self.new_session() as s:
            phonebook = self._get_phonebook(s, tenant_uuid, phonebook_id)
            return self._create_one(s, phonebook.id, contact_body)

    def create_many(self, tenant_uuid, phonebook_id, body):
        created = []
        errors = []
        with self.new_session() as s:
            phonebook = self._get_phonebook(s, tenant_uuid, phonebook_id)
            for contact_body in body:
                try:
                    contact = self._create_one(s, phonebook.id, contact_body)
                    created.append(contact)
                except Exception:
                    errors.append(contact_body)
        return created, errors

    def _create_one(self, session, phonebook_id, contact_body):
        hash_ = compute_contact_hash(contact_body)
        contact = Contact(phonebook_id=phonebook_id, hash=hash_)
        session.add(contact)
        self.flush_or_raise(session, DuplicatedContactException)
        self._add_field_to_contact(session, contact.uuid, contact_body)
        return contact_body

    def delete(self, tenant_uuid, phonebook_id, contact_id):
        with self.new_session() as s:
            phonebook = self._get_phonebook(s, tenant_uuid, phonebook_id)
            contact = self._get_contact(s, tenant_uuid, phonebook.id, contact_id)
            s.delete(contact)

    def edit(self, tenant_uuid, phonebook_id, contact_uuid, contact_body):
        hash_ = compute_contact_hash(contact_body)
        with self.new_session() as s:
            phonebook = self._get_phonebook(s, tenant_uuid, phonebook_id)
            contact = self._get_contact(s, tenant_uuid, phonebook.id, contact_uuid)
            contact.hash = hash_
            self.flush_or_raise(s, DuplicatedContactException)
            s.query(ContactFields).filter(
                ContactFields.contact_uuid == contact_uuid
            ).delete()
            self._add_field_to_contact(s, contact.uuid, contact_body)

        return contact_body

    def get(self, tenant_uuid, phonebook_id, contact_id):
        with self.new_session() as s:
            phonebook = self._get_phonebook(s, tenant_uuid, phonebook_id)
            filter_ = self._new_contact_filter(tenant_uuid, phonebook.id, contact_id)
            fields = s.query(ContactFields).join(Contact).filter(filter_).all()
            if not fields:
                raise NoSuchContact(contact_id)

            return {field.name: field.value for field in fields}

    def list(self, tenant_uuid, phonebook_id, search=None):
        with self.new_session() as s:
            phonebook = self._get_phonebook(s, tenant_uuid, phonebook_id)
            query = distinct(ContactFields.contact_uuid)
            matching_uuids = self._list_contacts(s, query, phonebook.id, search).all()
            if not matching_uuids:
                return []

            fields = (
                s.query(ContactFields)
                .filter(ContactFields.contact_uuid.in_(matching_uuids))
                .all()
            )
            result = defaultdict(dict)
            for field in fields:
                result[field.contact_uuid][field.name] = field.value

        return list(result.values())

    def _add_field_to_contact(self, s, contact_uuid, contact_body):
        contact_body['id'] = contact_uuid
        for name, value in contact_body.items():
            s.add(ContactFields(name=name, value=value, contact_uuid=contact_uuid))

    def _get_contact(self, s, tenant_uuid, phonebook_id, contact_uuid):
        filter_ = self._new_contact_filter(tenant_uuid, phonebook_id, contact_uuid)
        contact = s.query(Contact).join(Phonebook).filter(filter_).first()
        if not contact:
            raise NoSuchContact(contact_uuid)
        return contact

    def _get_phonebook(self, s, tenant_uuid, phonebook_id):
        filter_ = and_(
            Phonebook.id == phonebook_id, Phonebook.tenant_uuid == tenant_uuid
        )
        phonebook = s.query(Phonebook).filter(filter_).first()
        if not phonebook:
            raise NoSuchPhonebook(phonebook_id)
        return phonebook

    def _list_contacts(self, s, query, phonebook_id, search):
        filter_ = and_(
            Contact.phonebook_id == phonebook_id,
            ContactFields.value.ilike('%{}%'.format(search)) if search else True,
        )
        return s.query(query).join(Contact).join(Phonebook).filter(filter_)

    def _new_contact_filter(self, tenant_uuid, phonebook_id, contact_uuid):
        return and_(
            Contact.uuid == contact_uuid,
            Contact.phonebook_id == phonebook_id,
            Phonebook.tenant_uuid == tenant_uuid,
        )


class PhonebookCRUD(BaseDAO):
    _default_sort_order = 'name'
    _default_sort_direction = 'asc'

    def count(self, tenant_uuid, search=None):
        with self.new_session() as s:
            return self._count_by_tenant(s, tenant_uuid, search)

    def create(self, tenant_uuid, phonebook_body):
        with self.new_session() as s:
            self._create_tenant(s, tenant_uuid)
            phonebook = Phonebook(tenant_uuid=tenant_uuid, **phonebook_body)
            s.add(phonebook)
            self.flush_or_raise(s, DuplicatedPhonebookException)

            return self._phonebook_to_dict(phonebook)

    def delete(self, tenant_uuid, phonebook_id):
        with self.new_session() as s:
            phonebook = self._get_by_tenant_and_id(s, tenant_uuid, phonebook_id)
            s.delete(phonebook)

    def edit(self, tenant_uuid, phonebook_id, phonebook_body):
        with self.new_session() as s:
            phonebook = self._get_by_tenant_and_id(s, tenant_uuid, phonebook_id)
            for attribute_name, value in phonebook_body.items():
                if not hasattr(phonebook, attribute_name):
                    raise TypeError(
                        '{} has no attribute {}'.format(
                            phonebook.__class__.__name__, attribute_name
                        )
                    )
                setattr(phonebook, attribute_name, value)
            self.flush_or_raise(s, DuplicatedPhonebookException)
            return self._phonebook_to_dict(phonebook)

    def get(self, tenant_uuid, phonebook_id):
        with self.new_session() as s:
            phonebook = self._get_by_tenant_and_id(s, tenant_uuid, phonebook_id)
            return self._phonebook_to_dict(phonebook)

    def list(
        self,
        tenant_uuid,
        order=None,
        direction=None,
        limit=None,
        offset=None,
        search=None,
    ):
        with self.new_session() as s:
            phonebooks = self._get_by_tenant(
                s, tenant_uuid, order, direction, limit, offset, search
            )
            return [self._phonebook_to_dict(phonebook) for phonebook in phonebooks]

    def update_tenant(self, old_uuid, phonebook_id, new_uuid):
        with self.new_session() as s:
            self._create_tenant(s, new_uuid)
            filter_ = and_(
                Phonebook.id == Phonebook.id, Phonebook.tenant_uuid == old_uuid
            )
            phonebook = s.query(Phonebook).filter(filter_).first()
            phonebook.tenant_uuid = new_uuid
            s.flush()

    def _count_by_tenant(self, s, tenant_uuid, search):
        filter_ = self._new_tenant_filter(s, tenant_uuid, search)
        return s.query(func.count(Phonebook.id)).filter(filter_).scalar()

    def _get_by_tenant(self, s, tenant_uuid, order, direction, limit, offset, search):
        order_by_column_name = order or self._default_sort_order
        try:
            order_by_column = getattr(Phonebook, order_by_column_name)
        except AttributeError:
            raise TypeError(
                '{} has no attribute {}'.format(
                    Phonebook.__class__.__name__, order_by_column_name
                )
            )
        direction = direction or self._default_sort_direction
        order_by_column_and_direction = getattr(order_by_column, direction)()
        filter_ = self._new_tenant_filter(s, tenant_uuid, search)
        return (
            s.query(Phonebook)
            .filter(filter_)
            .order_by(order_by_column_and_direction)
            .limit(limit)
            .offset(offset)
            .all()
        )

    def _get_by_tenant_and_id(self, s, tenant_uuid, phonebook_id):
        filter_ = self._new_filter_by_tenant_and_id(s, tenant_uuid, phonebook_id)
        phonebook = s.query(Phonebook).filter(filter_).scalar()
        if not phonebook:
            raise NoSuchPhonebook(phonebook_id)

        return phonebook

    def _new_tenant_filter(self, s, tenant_uuid, search):
        if not search:
            return Phonebook.tenant_uuid == tenant_uuid
        else:
            pattern = '%{}%'.format(search)
            return and_(
                Phonebook.tenant_uuid == tenant_uuid,
                or_(
                    Phonebook.name.ilike(pattern), Phonebook.description.ilike(pattern)
                ),
            )

    def _new_filter_by_tenant_and_id(self, s, tenant_uuid, phonebook_id):
        return and_(Phonebook.id == phonebook_id, Phonebook.tenant_uuid == tenant_uuid)

    def _get_tenant(self, s, uuid):
        return s.query(Tenant).filter(Tenant.uuid == uuid).first()

    @staticmethod
    def _phonebook_to_dict(phonebook):
        return {
            'id': phonebook.id,
            'name': phonebook.name,
            'description': phonebook.description,
            'tenant_uuid': phonebook.tenant_uuid,
        }
