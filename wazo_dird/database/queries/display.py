# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from sqlalchemy import and_, func, text
from wazo_dird.database import schemas
from wazo_dird.exception import NoSuchDisplay
from .base import BaseDAO
from .. import Display, DisplayColumn


class DisplayCRUD(BaseDAO):

    _display_schema = schemas.DisplaySchema()

    def count(self, visible_tenants, **list_params):
        filter_ = self._list_filter(visible_tenants, **list_params)
        with self.new_session() as s:
            query = s.query(func.count(Display.uuid)).filter(filter_)
            return query.scalar()

    def create(self, tenant_uuid, name, columns, uuid=None):
        with self.new_session() as s:
            self._create_tenant(s, tenant_uuid)
            display = self._add_display(
                s, tenant_uuid=tenant_uuid, name=name, uuid=uuid
            )
            for column in columns:
                self._add_column(s, display_uuid=display.uuid, **column)
            s.flush()
            return self._display_schema.dump(display).data

    def delete(self, visible_tenants, display_uuid):
        filter_ = self._build_filter(visible_tenants, display_uuid)
        with self.new_session() as s:
            nb_deleted = (
                s.query(Display).filter(filter_).delete(synchronize_session=False)
            )

        if not nb_deleted:
            raise NoSuchDisplay(display_uuid)

    def edit(self, visible_tenants, display_uuid, name, columns):
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

    def get(self, visible_tenants, display_uuid):
        filter_ = self._build_filter(visible_tenants, display_uuid)
        with self.new_session() as s:
            display = s.query(Display).filter(filter_).first()
            if not display:
                raise NoSuchDisplay(display_uuid)

            return self._display_schema.dump(display).data

    def list_(self, visible_tenants, **list_params):
        filter_ = self._list_filter(visible_tenants, **list_params)
        with self.new_session() as s:
            query = s.query(Display).filter(filter_)
            query = self._paginate(query, **list_params)
            return self._display_schema.dump(query.all(), many=True).data

    def _build_filter(self, visible_tenants, display_uuid):
        if not visible_tenants and visible_tenants is not None:
            raise NoSuchDisplay(display_uuid)

        filter_ = Display.uuid == str(display_uuid)
        if visible_tenants:
            filter_ = and_(filter_, Display.tenant_uuid.in_(visible_tenants))

        return filter_

    def _list_filter(
        self, visible_tenants, uuid=None, name=None, search=None, **list_params
    ):
        filter_ = text('true')
        if visible_tenants is not None:
            filter_ = and_(filter_, Display.tenant_uuid.in_(visible_tenants))
        if uuid is not None:
            filter_ = and_(filter_, Display.uuid == uuid)
        if name is not None:
            filter_ = and_(filter_, Display.name == name)
        if search is not None:
            pattern = '%{}%'.format(search)
            filter_ = and_(filter_, Display.name.ilike(pattern))
        return filter_

    def _paginate(
        self, query, limit=None, offset=None, order=None, direction=None, **ignored
    ):
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
    def _add_column(session, **column_body):
        column = DisplayColumn(**column_body)
        session.add(column)

    @staticmethod
    def _add_display(session, **display_body):
        display = Display(**display_body)
        session.add(display)
        session.flush()
        return display
