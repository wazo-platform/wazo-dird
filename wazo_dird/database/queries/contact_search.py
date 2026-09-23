# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Any, ClassVar

from sqlalchemy import and_, distinct, select
from sqlalchemy.orm import scoped_session
from sqlalchemy.sql.expression import ColumnElement

from .. import Contact, ContactFields
from .base import (
    BaseDAO,
    ContactInfo,
    build_exten_contact_map,
    list_contacts_by_uuid,
    search_pattern,
)


class ContactSearchEngine(BaseDAO):
    """Query shape shared by the personal and phonebook search engines.

    A subclass names the table owning a contact and supplies the scope: the
    predicate restricting a query to the contacts its caller may see. Personal
    contacts are scoped per call, phonebooks per instance, so the scope is
    passed in rather than read from the subclass.
    """

    # the table joined to Contact to reach the owner, User or Phonebook
    _owner_model: ClassVar[Any]

    def __init__(
        self,
        Session: scoped_session,
        searched_columns: list[str] | None = None,
        first_match_columns: list[str] | None = None,
    ) -> None:
        super().__init__(Session)
        self._searched_columns = searched_columns or []
        self._first_match_columns = first_match_columns or []

    def _search_filter(self, term: str) -> ColumnElement | bool:
        if not self._searched_columns:
            return False

        pattern = search_pattern(term)
        if pattern is None:
            return False

        return and_(
            ContactFields.normalized_value.ilike(pattern),
            ContactFields.name.in_(self._searched_columns),
        )

    def _first_match_filter(self, term: str) -> ColumnElement | bool:
        if not self._first_match_columns:
            return False

        # phone numbers: exact match, relies on btree indexing of value
        return and_(
            ContactFields.value == term,
            ContactFields.name.in_(self._first_match_columns),
        )

    @staticmethod
    def _list_filter(contact_uuids: list[str]) -> ColumnElement | bool:
        if not contact_uuids:
            return False

        return ContactFields.contact_uuid.in_(contact_uuids)

    def _find_contacts(
        self,
        scope: ColumnElement | bool,
        filter_: ColumnElement | bool | None = None,
        limit: int | None = None,
    ) -> list[ContactInfo]:
        if scope is False or filter_ is False:
            return []

        criteria = scope if filter_ is None else and_(filter_, scope)
        with self.new_session() as s:
            query = (
                s.query(distinct(ContactFields.contact_uuid))
                .join(Contact)
                .join(self._owner_model)
                .filter(criteria)
            )
            if limit:
                query = query.limit(limit)

            uuids = [uuid for (uuid,) in query.all()]

            return list_contacts_by_uuid(s, uuids)

    def _find_contacts_for_extens(
        self, scope: ColumnElement | bool, extens: list[str]
    ) -> dict[str, ContactInfo]:
        if scope is False or not extens or not self._first_match_columns:
            return {}

        matched_uuids = (
            select(ContactFields.contact_uuid)
            .join(Contact)
            .join(self._owner_model)
            .where(
                ContactFields.value.in_(extens),
                ContactFields.name.in_(self._first_match_columns),
                scope,
            )
            .distinct()
            .scalar_subquery()
        )
        with self.new_session() as s:
            rows = (
                s.query(
                    ContactFields.contact_uuid, ContactFields.name, ContactFields.value
                )
                .filter(ContactFields.contact_uuid.in_(matched_uuids))
                .all()
            )
            return build_exten_contact_map(rows, extens, self._first_match_columns)
