# Copyright 2019-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import builtins
import logging
from collections import defaultdict
from typing import Any, TypedDict, cast

from sqlalchemy import and_, distinct, func, or_, text
from sqlalchemy.orm import Query
from sqlalchemy.orm import Session as BaseSession
from sqlalchemy.orm import scoped_session
from sqlalchemy.sql.expression import ColumnElement

from wazo_dird.database.queries.base import Direction
from wazo_dird.exception import (
    DuplicatedContactException,
    DuplicatedPhonebookException,
    NoSuchContact,
    NoSuchPhonebook,
)

from .. import Contact, ContactFields, Phonebook
from .base import BaseDAO, ContactInfo, compute_contact_hash, list_contacts_by_uuid

logger = logging.getLogger(__name__)


class PhonebookKey(TypedDict, total=False):
    id: int
    uuid: str


class PhonebookDict(TypedDict):
    id: int
    uuid: str
    description: str
    name: str
    tenant_uuid: str


def phonebook_key_to_filter(phonebook_key: PhonebookKey) -> ColumnElement:
    assert 'id' in phonebook_key or 'uuid' in phonebook_key
    return (
        Phonebook.uuid == phonebook_key['uuid']
        if 'uuid' in phonebook_key
        else Phonebook.id == phonebook_key['id']
    )


class PhonebookContactSearchEngine(BaseDAO):
    def __init__(
        self,
        Session: scoped_session,
        visible_tenants: list[str] | None,
        phonebook_key: PhonebookKey,
        searched_columns: list[str] | None = None,
        first_match_columns: list[str] | None = None,
    ):
        super().__init__(Session)
        self._searched_columns = searched_columns
        self._first_match_columns = first_match_columns
        self._visible_tenants = visible_tenants
        self._phonebook_key = phonebook_key

    def find_contacts(self, term: str) -> list[ContactInfo]:
        pattern = f'%{term}%'
        filter_ = self._new_search_filter(pattern, self._searched_columns)
        with self.new_session() as s:
            return self._find_contacts_with_filter(s, filter_)

    def find_first_contact(self, term: str) -> ContactInfo | None:
        filter_ = self._new_search_filter(term, self._first_match_columns)
        with self.new_session() as s:
            for contact in self._find_contacts_with_filter(s, filter_, limit=1):
                return contact
            else:
                return None

    def list_contacts(self, contact_uuids: list[str]) -> list[ContactInfo]:
        filter_ = self._new_list_filter(contact_uuids)
        with self.new_session() as s:
            return self._find_contacts_with_filter(s, filter_)

    def _find_contacts_with_filter(
        self, s: BaseSession, filter_: ColumnElement, limit: int | None = None
    ) -> list[ContactInfo]:
        phonebook_filter = phonebook_key_to_filter(self._phonebook_key)
        if self._visible_tenants is None:
            _filter = and_(filter_, phonebook_filter)
        elif not self._visible_tenants:
            _filter = text('false')
        else:
            _filter = and_(
                filter_,
                phonebook_filter,
                Phonebook.tenant_uuid.in_(self._visible_tenants),
            )
        query = (
            s.query(distinct(ContactFields.contact_uuid))
            .join(Contact)
            .join(Phonebook)
            .filter(_filter)
        )

        if limit:
            query = query.limit(limit)

        uuids = [uuid for (uuid,) in query.all()]

        return list_contacts_by_uuid(s, uuids)

    def _new_list_filter(self, contact_uuids: list[str]) -> bool | ColumnElement:
        if not contact_uuids:
            return False

        return ContactFields.contact_uuid.in_(contact_uuids)

    def _new_search_filter(
        self, pattern: str, columns: list[str]
    ) -> bool | ColumnElement:
        if not columns:
            return False

        return and_(ContactFields.value.ilike(pattern), ContactFields.name.in_(columns))


def contact_search_filter(search):
    search_filter = (
        Contact.uuid.in_(
            Query(ContactFields.contact_uuid)
            .join(Contact)
            .filter(ContactFields.value.ilike(f'%{search}%'))
            .subquery()
        )
        if search
        else True
    )
    return search_filter


class PhonebookContactCRUD(BaseDAO):
    def count(
        self,
        visible_tenants: list[str] | None,
        phonebook_key: PhonebookKey,
        search: str | None = None,
    ) -> int:
        with self.new_session() as s:
            logger.debug(
                "counting contacts for phonebook %s with visible tenants %s given search term %s",
                str(phonebook_key),
                str(visible_tenants),
                search,
            )
            phonebook = self._get_phonebook(s, visible_tenants, phonebook_key)
            logger.debug(
                "Found phonebook (name=%s) from key (%s)",
                phonebook.name,
                str(phonebook_key),
            )
            query = self._query_contacts(
                s,
                phonebook_key=PhonebookKey(uuid=phonebook.uuid),
                search=search,
            ).with_entities(func.count(distinct(Contact.uuid)))
            logger.debug("Counting contacts with query: %s", str(query.statement))
            return query.scalar()

    def create(
        self,
        visible_tenants: list[str] | None,
        phonebook_key: PhonebookKey,
        contact_body: dict,
    ) -> ContactInfo:
        with self.new_session() as s:
            phonebook = self._get_phonebook(s, visible_tenants, phonebook_key)
            return self._create_one(
                s,
                phonebook.tenant_uuid,
                PhonebookKey(uuid=phonebook.uuid),
                contact_body,
            )

    def create_many(
        self,
        visible_tenants: list[str] | None,
        phonebook_key: PhonebookKey,
        body: list[dict],
    ) -> tuple[list[ContactInfo], list[dict]]:
        created = []
        errors = []
        with self.new_session() as s:
            phonebook = self._get_phonebook(s, visible_tenants, phonebook_key)
            for contact_body in body:
                try:
                    contact = self._create_one(
                        s,
                        phonebook.tenant_uuid,
                        PhonebookKey(uuid=phonebook.uuid),
                        contact_body,
                    )
                    created.append(contact)
                except Exception:
                    errors.append(contact_body)
        return created, errors

    def _create_one(
        self,
        session: BaseSession,
        tenant_uuid: str,
        phonebook_key: PhonebookKey,
        contact_body: dict,
    ) -> ContactInfo:
        hash_ = compute_contact_hash(contact_body)
        contact = Contact(
            phonebook=self._get_phonebook(session, [tenant_uuid], phonebook_key),
            hash=hash_,
        )
        session.add(contact)
        self.flush_or_raise(session, DuplicatedContactException)
        self._add_fields_to_contact(session, contact.uuid, contact_body)
        return cast(ContactInfo, contact_body)

    def delete(
        self,
        visible_tenants: list[str] | None,
        phonebook_key: PhonebookKey,
        contact_uuid: str,
    ):
        with self.new_session() as s:
            phonebook = self._get_phonebook(s, visible_tenants, phonebook_key)
            contact = self._get_contact(
                s,
                phonebook.tenant_uuid,
                PhonebookKey(uuid=phonebook.uuid),
                contact_uuid,
            )
            s.delete(contact)

    def edit(
        self,
        visible_tenants: list[str] | None,
        phonebook_key: PhonebookKey,
        contact_uuid: str,
        contact_body: dict,
    ) -> ContactInfo:
        hash_ = compute_contact_hash(contact_body)
        with self.new_session() as s:
            phonebook = self._get_phonebook(s, visible_tenants, phonebook_key)
            contact = self._get_contact(
                s,
                phonebook.tenant_uuid,
                PhonebookKey(uuid=phonebook.uuid),
                contact_uuid,
            )
            contact.hash = hash_
            self.flush_or_raise(s, DuplicatedContactException)
            s.query(ContactFields).filter(
                ContactFields.contact_uuid == contact_uuid
            ).delete()
            self._add_fields_to_contact(s, contact.uuid, contact_body)

        return cast(ContactInfo, contact_body)

    def get(
        self,
        visible_tenants: list[str] | None,
        phonebook_key: PhonebookKey,
        contact_uuid: str,
    ) -> ContactInfo:
        with self.new_session() as s:
            phonebook = self._get_phonebook(s, visible_tenants, phonebook_key)
            filter_ = self._new_contact_filter(
                phonebook.tenant_uuid, PhonebookKey(uuid=phonebook.uuid), contact_uuid
            )
            fields = s.query(ContactFields).join(Contact).filter(filter_).all()
            if not fields:
                raise NoSuchContact(contact_uuid)
            contact_info = {field.name: field.value for field in fields}
            assert 'id' in contact_info
            return cast(ContactInfo, contact_info)

    def list(
        self,
        visible_tenants: list[str] | None,
        phonebook_key: PhonebookKey,
        search: str | None = None,
    ) -> list[ContactInfo]:
        with self.new_session() as s:
            phonebook = self._get_phonebook(s, visible_tenants, phonebook_key)
            fields = self._list_contact_fields(
                s,
                phonebook_key=PhonebookKey(uuid=phonebook.uuid),
                search=search,
            )

            result: dict[str, dict[str, Any]] = defaultdict(dict)
            for field in fields:
                result[field.contact_uuid][field.name] = field.value

        return cast(list[ContactInfo], list(result.values()))

    def _add_fields_to_contact(
        self, s: BaseSession, contact_uuid: str, contact_body: dict
    ):
        contact_body['id'] = contact_uuid
        for name, value in contact_body.items():
            s.add(ContactFields(name=name, value=value, contact_uuid=contact_uuid))

    def _get_contact(
        self,
        s: BaseSession,
        tenant_uuid: str,
        phonebook_key: PhonebookKey,
        contact_uuid: str,
    ) -> Contact:
        filter_ = self._new_contact_filter(tenant_uuid, phonebook_key, contact_uuid)
        contact = s.query(Contact).join(Phonebook).filter(filter_).first()
        if not contact:
            raise NoSuchContact(contact_uuid)
        return contact

    def _get_phonebook(
        self,
        s: BaseSession,
        visible_tenants: builtins.list[str] | None,
        phonebook_key: PhonebookKey,
    ) -> Phonebook:
        filter_ = phonebook_selector(visible_tenants, phonebook_key)

        phonebook = s.query(Phonebook).filter(filter_).first()
        if not phonebook:
            raise NoSuchPhonebook(
                cast(dict, phonebook_key), tenants_in_scope=visible_tenants
            )
        return phonebook

    def _build_phonebook_filter(self, phonebook_key: PhonebookKey):
        assert 'id' in phonebook_key or 'uuid' in phonebook_key
        return (
            Contact.phonebook_uuid == phonebook_key['uuid']
            if 'uuid' in phonebook_key
            else (
                Contact.phonebook_uuid
                == Query(Phonebook.uuid)
                .filter(Phonebook.id == phonebook_key['id'])
                .subquery()
            )
        )

    def _query_contacts(
        self,
        s: BaseSession,
        phonebook_key: PhonebookKey,
        search: str | None = None,
    ) -> Query:
        phonebook_filter = self._build_phonebook_filter(phonebook_key)
        search_filter = contact_search_filter(search)
        filter_ = and_(phonebook_filter, search_filter)
        query = s.query(Contact).join(Phonebook).filter(filter_)
        return query

    def _query_contact_fields(
        self,
        s: BaseSession,
        phonebook_key: PhonebookKey,
        search: str | None,
    ):
        phonebook_filter = self._build_phonebook_filter(phonebook_key)
        search_filter = contact_search_filter(search)
        filter_ = and_(
            phonebook_filter,
            search_filter,
        )
        query = s.query(ContactFields).join(Contact).join(Phonebook).filter(filter_)
        return query

    def _list_contact_fields(
        self,
        s: BaseSession,
        phonebook_key: PhonebookKey,
        search: str | None = None,
    ) -> builtins.list[ContactFields]:
        query = self._query_contact_fields(
            s, phonebook_key=phonebook_key, search=search
        )
        logger.debug("listing contact fields with query %s", str(query.statement))
        return query.all()

    def _new_contact_filter(
        self, tenant_uuid: str, phonebook_key: PhonebookKey, contact_uuid: str
    ):
        phonebook_filter = self._build_phonebook_filter(phonebook_key)
        return and_(
            Contact.uuid == contact_uuid,
            phonebook_filter,
            Phonebook.tenant_uuid == tenant_uuid,
        )


def phonebook_selector(
    visible_tenants: list[str] | None, phonebook_key: PhonebookKey
) -> ColumnElement:
    key_filter = phonebook_key_to_filter(phonebook_key)
    if visible_tenants is None:  # disable tenant filter
        return key_filter
    elif not visible_tenants:  # empty tenant scope
        return text('false')
    else:
        return and_(
            key_filter,
            Phonebook.tenant_uuid.in_(visible_tenants),
        )


def phonebook_search_filter(
    visible_tenants: list[str] | None, search: str | None
) -> ColumnElement:
    if not search:
        if visible_tenants is None:  # disable tenant filter
            return text('true')
        elif not visible_tenants:  # empty tenant scope
            return text('false')
        else:
            return Phonebook.tenant_uuid.in_(visible_tenants)
    else:
        pattern = f'%{search}%'
        return and_(
            Phonebook.tenant_uuid.in_(visible_tenants),
            or_(Phonebook.name.ilike(pattern), Phonebook.description.ilike(pattern)),
        )


class PhonebookCRUD(BaseDAO):
    _default_sort_order: str = 'name'
    _default_sort_direction: Direction = 'asc'

    def count(
        self, visible_tenants: list[str] | None, search: str | None = None
    ) -> int:
        with self.new_session() as s:
            return self._count_by_tenant(s, visible_tenants, search)

    def create(self, tenant_uuid: str, phonebook_body: dict) -> PhonebookDict:
        with self.new_session() as s:
            self._create_tenant(s, tenant_uuid)
            phonebook = Phonebook(tenant_uuid=tenant_uuid, **phonebook_body)
            s.add(phonebook)
            self.flush_or_raise(s, DuplicatedPhonebookException)

            return self._phonebook_to_dict(phonebook)

    def delete(self, visible_tenants: list[str] | None, phonebook_key: PhonebookKey):
        with self.new_session() as s:
            phonebook = self._get_by_tenant_and_id(s, visible_tenants, phonebook_key)
            s.delete(phonebook)

    def edit(
        self,
        visible_tenants: list[str] | None,
        phonebook_key: PhonebookKey,
        phonebook_body: dict,
    ) -> PhonebookDict:
        with self.new_session() as s:
            phonebook = self._get_by_tenant_and_id(s, visible_tenants, phonebook_key)
            for attribute_name, value in phonebook_body.items():
                if not hasattr(phonebook, attribute_name):
                    raise TypeError(
                        f'{phonebook.__class__.__name__} has no attribute {attribute_name}'
                    )
                setattr(phonebook, attribute_name, value)
            self.flush_or_raise(s, DuplicatedPhonebookException)
            return self._phonebook_to_dict(phonebook)

    def get(
        self, visible_tenants: list[str] | None, phonebook_key: PhonebookKey
    ) -> PhonebookDict:
        with self.new_session() as s:
            phonebook = self._get_by_tenant_and_id(s, visible_tenants, phonebook_key)
            return self._phonebook_to_dict(phonebook)

    def list(
        self,
        visible_tenants: builtins.list[str] | None,
        order: str | None = None,
        direction: Direction | None = None,
        limit: int | None = None,
        offset: int | None = None,
        search: str | None = None,
    ) -> builtins.list[PhonebookDict]:
        with self.new_session() as s:
            phonebooks = self._get_by_tenant(
                s, visible_tenants, order, direction, limit, offset, search
            )
            return [self._phonebook_to_dict(phonebook) for phonebook in phonebooks]

    def update_tenant(
        self,
        visible_tenants: builtins.list[str] | None,
        phonebook_key: PhonebookKey,
        new_uuid: str,
    ):
        with self.new_session() as s:
            self._create_tenant(s, new_uuid)
            filter_ = and_(
                phonebook_key_to_filter(phonebook_key),
                Phonebook.tenant_uuid.in_(visible_tenants),
            )
            phonebook = s.query(Phonebook).filter(filter_).first()
            phonebook.tenant_uuid = new_uuid
            s.flush()

    def _count_by_tenant(
        self,
        s: BaseSession,
        visible_tenants: builtins.list[str] | None,
        search: str | None,
    ) -> int:
        filter_ = phonebook_search_filter(visible_tenants, search)
        return s.query(func.count(Phonebook.uuid)).filter(filter_).scalar()

    def _get_by_tenant(
        self,
        s: BaseSession,
        visible_tenants: builtins.list[str] | None,
        order: str | None,
        direction: Direction | None,
        limit: int | None,
        offset: int | None,
        search: str | None,
    ) -> builtins.list[Phonebook]:
        order_by_column_name = order or self._default_sort_order
        try:
            order_by_column = getattr(Phonebook, order_by_column_name)
        except AttributeError:
            raise TypeError(
                f'{Phonebook.__class__.__name__} has no attribute {order_by_column_name}'
            )
        direction = direction or self._default_sort_direction
        order_by_column_and_direction = getattr(order_by_column, direction)()
        filter_ = phonebook_search_filter(visible_tenants, search)
        return (
            s.query(Phonebook)
            .filter(filter_)
            .order_by(order_by_column_and_direction)
            .limit(limit)
            .offset(offset)
            .all()
        )

    def _get_by_tenant_and_id(
        self, s, visible_tenants: builtins.list[str] | None, phonebook_key: PhonebookKey
    ) -> Phonebook:
        filter_ = phonebook_selector(visible_tenants, phonebook_key)
        phonebook = s.query(Phonebook).filter(filter_).scalar()
        if not phonebook:
            raise NoSuchPhonebook(cast(dict, phonebook_key))

        return phonebook

    @staticmethod
    def _phonebook_to_dict(phonebook: Phonebook) -> PhonebookDict:
        return PhonebookDict(
            id=phonebook.id,
            uuid=phonebook.uuid,
            name=phonebook.name,
            description=phonebook.description,
            tenant_uuid=phonebook.tenant_uuid,
        )
