# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, func, text
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql.elements import ClauseElement

from wazo_dird.database import schemas
from wazo_dird.database.queries.base import Direction
from wazo_dird.exception import NoSuchDisplay

from .. import Display, DisplayColumn
from .base import BaseDAO


class DisplayCRUD(BaseDAO):
    _display_schema = schemas.DisplaySchema()

    def count(self, visible_tenants: list[str] | None, **list_params: Any) -> int:
        filter_ = self._list_filter(visible_tenants, **list_params)
        with self.new_session() as s:
            query = s.query(func.count(Display.uuid)).filter(filter_)
            count: int = query.scalar()
            return count

    def create(
        self,
        tenant_uuid: str,
        name: str,
        columns: list[dict[str, Any]],
        uuid: str | None = None,
    ) -> dict[str, Any]:
        with self.new_session() as s:
            self._create_tenant(s, tenant_uuid)
            display = self._add_display(
                s, tenant_uuid=tenant_uuid, name=name, uuid=uuid
            )
            for column in columns:
                self._add_column(s, display_uuid=display.uuid, **column)
            s.flush()
            result: dict[str, Any] = self._display_schema.dump(display)
            return result

    def delete(self, visible_tenants: list[str] | None, display_uuid: str) -> None:
        filter_ = self._build_filter(visible_tenants, display_uuid)
        with self.new_session() as s:
            nb_deleted = (
                s.query(Display).filter(filter_).delete(synchronize_session=False)
            )

        if not nb_deleted:
            raise NoSuchDisplay(display_uuid)

    def edit(
        self,
        visible_tenants: list[str] | None,
        display_uuid: str,
        name: str,
        columns: list[dict[str, Any]],
    ) -> None:
        filter_ = self._build_filter(visible_tenants, display_uuid)
        with self.new_session() as s:
            display = s.query(Display).filter(filter_).first()
            if not display:
                raise NoSuchDisplay(display_uuid)

            s.query(DisplayColumn).filter(
                DisplayColumn.display_uuid == display_uuid
            ).delete(synchronize_session=False)

            display.name = name
            for column in columns:
                self._add_column(s, display_uuid=display_uuid, **column)

    def get(
        self, visible_tenants: list[str] | None, display_uuid: str
    ) -> dict[str, Any]:
        filter_ = self._build_filter(visible_tenants, display_uuid)
        with self.new_session() as s:
            display = s.query(Display).filter(filter_).first()
            if not display:
                raise NoSuchDisplay(display_uuid)

            result: dict[str, Any] = self._display_schema.dump(display)
            return result

    def list_(
        self, visible_tenants: list[str] | None, **list_params: Any
    ) -> list[dict[str, Any]]:
        filter_ = self._list_filter(visible_tenants, **list_params)
        with self.new_session() as s:
            query = s.query(Display).filter(filter_)
            query = self._paginate(query, **list_params)
            result: list[dict[str, Any]] = self._display_schema.dump(
                query.all(), many=True
            )
            return result

    def _build_filter(
        self, visible_tenants: list[str] | None, display_uuid: str
    ) -> ClauseElement:
        if not visible_tenants and visible_tenants is not None:
            raise NoSuchDisplay(display_uuid)

        filter_: ClauseElement = Display.uuid == str(display_uuid)
        if visible_tenants:
            filter_ = and_(filter_, Display.tenant_uuid.in_(visible_tenants))

        return filter_

    def _list_filter(
        self,
        visible_tenants: list[str] | None,
        uuid: str | None = None,
        name: str | None = None,
        search: str | None = None,
        **list_params: Any,
    ) -> ClauseElement:
        filter_: ClauseElement = text('true')
        if visible_tenants is not None:
            filter_ = and_(filter_, Display.tenant_uuid.in_(visible_tenants))
        if uuid is not None:
            filter_ = and_(filter_, Display.uuid == uuid)
        if name is not None:
            filter_ = and_(filter_, Display.name == name)
        if search is not None:
            pattern = f'%{search}%'
            filter_ = and_(filter_, Display.name.ilike(pattern))
        return filter_

    def _paginate(
        self,
        query: Query,
        limit: int | None = None,
        offset: int | None = None,
        order: str | None = None,
        direction: Direction | None = None,
        **ignored: Any,
    ) -> Query:
        if order and direction:
            field = None
            if order == 'name':
                field = Display.name

            if field:
                order_clause = field.asc() if direction == 'asc' else field.desc()
                query = query.order_by(order_clause)

        if limit is not None:
            query = query.limit(limit)

        if offset is not None:
            query = query.offset(offset)

        return query

    @staticmethod
    def _add_column(session: Session, **column_body: Any) -> None:
        column = DisplayColumn(**column_body)
        session.add(column)

    @staticmethod
    def _add_display(session: Session, **display_body: Any) -> Display:
        display = Display(**display_body)
        session.add(display)
        session.flush()
        return display
