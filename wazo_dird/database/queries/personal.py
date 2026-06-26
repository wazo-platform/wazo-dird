# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import and_, distinct, text
from sqlalchemy.orm import Session as BaseSession
from sqlalchemy.orm import scoped_session
from sqlalchemy.sql.expression import ColumnElement
from sqlalchemy.sql.functions import ReturnTypeFromArgs
from unidecode import unidecode

from wazo_dird.exception import DuplicatedContactException, NoSuchContact
from wazo_dird.plugin_helpers.sorting import sort_contacts

from .. import Contact, ContactFields, User
from .base import BaseDAO, ContactInfo, compute_contact_hash, list_contacts_by_uuid


class unaccent(ReturnTypeFromArgs):
    inherit_cache = True


class PersonalContactSearchEngine(BaseDAO):
    def __init__(
        self,
        Session: scoped_session,
        searched_columns: list[str] | None = None,
        first_match_columns: list[str] | None = None,
    ) -> None:
        super().__init__(Session)
        self._searched_columns = searched_columns or []
        self._first_match_columns = first_match_columns or []

    def find_first_personal_contact(
        self, user_uuid: str, term: str
    ) -> list[ContactInfo]:
        filter_ = self._new_strict_filter(user_uuid, term, self._first_match_columns)
        return self._find_personal_contacts_with_filter(filter_, limit=1)

    def find_personal_contacts(self, user_uuid: str, term: str) -> list[ContactInfo]:
        filter_ = self._new_search_filter(user_uuid, term, self._searched_columns)
        return self._find_personal_contacts_with_filter(filter_)

    def list_personal_contacts(
        self, user_uuid: str, uuids: list[str] | None = None
    ) -> list[ContactInfo]:
        if uuids is None:
            filter_ = self._new_user_contacts_filter(user_uuid)
        else:
            filter_ = self._new_list_filter(user_uuid, uuids)
        return self._find_personal_contacts_with_filter(filter_)

    def _find_personal_contacts_with_filter(
        self, filter_: bool | ColumnElement, limit: int | None = None
    ) -> list[ContactInfo]:
        if filter_ is False:
            return []

        with self.new_session() as s:
            base_query = (
                s.query(distinct(ContactFields.contact_uuid))
                .join(Contact)
                .join(User)
                .filter(filter_)
            )
            if limit:
                query = base_query.limit(limit)
            else:
                query = base_query

            uuids = [uuid for (uuid,) in query.all()]

            return list_contacts_by_uuid(s, uuids)

    def _new_list_filter(
        self, user_uuid: str, uuids: list[str]
    ) -> bool | ColumnElement:
        if not uuids:
            return False

        return and_(User.user_uuid == user_uuid, ContactFields.contact_uuid.in_(uuids))

    def _new_search_filter(
        self, user_uuid: str, term: str, columns: list[str]
    ) -> bool | ColumnElement:
        if not columns:
            return False

        pattern = f'%{unidecode(term)}%'
        return and_(
            User.user_uuid == user_uuid,
            unaccent(ContactFields.value).ilike(pattern),
            ContactFields.name.in_(columns),
        )

    def _new_strict_filter(
        self, user_uuid: str, term: str, columns: list[str]
    ) -> bool | ColumnElement:
        if not columns:
            return False

        return and_(
            User.user_uuid == user_uuid,
            unaccent(ContactFields.value) == unidecode(term),
            ContactFields.name.in_(columns),
        )

    def _new_user_contacts_filter(self, user_uuid: str) -> ColumnElement:
        return User.user_uuid == user_uuid


class PersonalContactCRUD(BaseDAO):
    def list_personal_contacts(
        self,
        user_uuid: str | None = None,
        search_params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        filter_ = text('true')
        if user_uuid:
            filter_ = and_(filter_, Contact.user_uuid == user_uuid)

        order, limit, offset, direction = self._extract_pagination_params(search_params)

        with self.new_session() as s:
            query = s.query(distinct(Contact.uuid)).filter(filter_)
            contact_uuids = [uuid for (uuid,) in query.all()]
            contacts = cast(
                list[dict[str, Any]], list_contacts_by_uuid(s, contact_uuids)
            )

        if order and contacts and not any(order in contact for contact in contacts):
            raise ValueError(f"order: column '{order}' was not found")
        contacts = sort_contacts(
            contacts, order=order, direction=direction, order_insensitive=True
        )
        return contacts[offset : offset + limit if limit else None]

    def create_personal_contact(
        self, tenant_uuid: str, user_uuid: str, contact_info: dict[str, Any]
    ) -> dict[str, Any] | None:
        with self.new_session() as s:
            for contact in self._create_personal_contacts(
                s, tenant_uuid, user_uuid, [contact_info], fail_on_duplicate=True
            ):
                return contact
        return None

    def create_personal_contacts(
        self,
        tenant_uuid: str,
        user_uuid: str,
        contact_infos: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        with self.new_session() as s:
            return self._create_personal_contacts(
                s, tenant_uuid, user_uuid, contact_infos
            )

    def _create_personal_contacts(
        self,
        session: BaseSession,
        tenant_uuid: str,
        user_uuid: str,
        contact_infos: list[dict[str, Any]],
        fail_on_duplicate: bool = False,
    ) -> list[dict[str, Any]]:
        hash_and_contact = {compute_contact_hash(c): c for c in contact_infos}
        user = self._get_dird_user(session, tenant_uuid, user_uuid)
        existing_hashes_and_id = self._find_existing_contact_by_hash(
            session, user_uuid, list(hash_and_contact.keys())
        )
        all_hashes = set(hash_and_contact.keys())
        to_add = all_hashes - set(existing_hashes_and_id.keys())
        existing = all_hashes - to_add
        if existing and fail_on_duplicate:
            raise DuplicatedContactException()

        for hash_ in to_add:
            contact_info = hash_and_contact[hash_]
            contact_args = {'user_uuid': user.user_uuid, 'hash': hash_}
            contact_uuid = contact_info.get('id')
            if contact_uuid:
                contact_args['uuid'] = contact_uuid
            contact = Contact(**contact_args)
            session.add(contact)
            session.flush()

            contact_info['id'] = contact.uuid
            for name, value in contact_info.items():
                session.add(
                    ContactFields(name=name, value=value, contact_uuid=contact.uuid)
                )

        for hash_ in existing:
            contact_info = hash_and_contact[hash_]
            contact_info['id'] = existing_hashes_and_id[hash_]

        return contact_infos

    def _find_existing_contact_by_hash(
        self, session: BaseSession, user_uuid: str, hashes: list[str]
    ) -> dict[str, str]:
        if not hashes:
            return {}

        filter_ = and_(Contact.user_uuid == user_uuid, Contact.hash.in_(hashes))
        pairs = session.query(Contact.hash, Contact.uuid).filter(filter_)
        return {p.hash: p.uuid for p in pairs.all()}

    def edit_personal_contact(
        self,
        tenant_uuid: str,
        user_uuid: str,
        contact_id: str,
        contact_info: dict[str, Any],
    ) -> dict[str, Any] | None:
        with self.new_session() as s:
            self._delete_personal_contact(s, user_uuid, contact_id)
            hash_ = compute_contact_hash(contact_info)
            if self._find_existing_contact_by_hash(s, user_uuid, [hash_]):
                s.rollback()
                raise DuplicatedContactException()
            contact_info['id'] = contact_id
            for contact in self._create_personal_contacts(
                s, tenant_uuid, user_uuid, [contact_info]
            ):
                return contact
        return None

    def get_personal_contact(self, user_uuid: str, contact_uuid: str) -> ContactInfo:
        with self.new_session() as s:
            filter_ = and_(
                User.user_uuid == user_uuid, ContactFields.contact_uuid == contact_uuid
            )
            contact_uuids = (
                s.query(distinct(ContactFields.contact_uuid))
                .join(Contact)
                .join(User)
                .filter(filter_)
            )

            for contact in list_contacts_by_uuid(s, contact_uuids):
                return contact

        raise NoSuchContact(contact_uuid)

    def delete_all_personal_contacts(self, user_uuid: str) -> int:
        with self.new_session() as s:
            filter_ = User.user_uuid == user_uuid
            return self._delete_personal_contacts_with_filter(s, filter_)

    def delete_personal_contact(self, user_uuid: str, contact_uuid: str) -> None:
        with self.new_session() as s:
            self._delete_personal_contact(s, user_uuid, contact_uuid)

    def _delete_personal_contact(
        self, session: BaseSession, user_uuid: str, contact_uuid: str
    ) -> None:
        filter_ = and_(
            User.user_uuid == user_uuid, ContactFields.contact_uuid == contact_uuid
        )
        nb_deleted = self._delete_personal_contacts_with_filter(session, filter_)
        if nb_deleted == 0:
            raise NoSuchContact(contact_uuid)

    def _delete_personal_contacts_with_filter(
        self, session: BaseSession, filter_: bool | ColumnElement
    ) -> int:
        contacts = (
            session.query(Contact).join(ContactFields).join(User).filter(filter_).all()
        )
        deleted = 0
        for contact in contacts:
            session.delete(contact)
            deleted += 1
        return deleted
