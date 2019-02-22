# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from sqlalchemy import (
    and_,
    text,
)
from wazo_dird.exception import NoSuchDisplay
from .base import BaseDAO
from ..import (
    Display,
    DisplayColumn,
)


class DisplayCRUD(BaseDAO):

    def create(self, tenant_uuid, name, columns):
        with self.new_session() as s:
            self._create_tenant(s, tenant_uuid)
            uuid = self._add_display(s, tenant_uuid=tenant_uuid, name=name)
            for column in columns:
                self._add_column(s, display_uuid=uuid, **column)

        return {
            'uuid': uuid,
            'tenant_uuid': tenant_uuid,
            'name': name,
            'columns': columns,
        }

    def delete(self, visible_tenants, display_uuid):
        filter_ = self._build_filter(visible_tenants, display_uuid)
        with self.new_session() as s:
            nb_deleted = s.query(Display).filter(filter_).delete(synchronize_session=False)

        if not nb_deleted:
            raise NoSuchDisplay(display_uuid)

    def get(self, visible_tenants, display_uuid):
        filter_ = self._build_filter(visible_tenants, display_uuid)
        with self.new_session() as s:
            display = s.query(Display).filter(filter_).first()
            if not display:
                raise NoSuchDisplay(display_uuid)

            return self._from_db_format(display)

    def list_(self, visible_tenants, **list_params):
        filter_ = self._list_filter(visible_tenants, **list_params)
        with self.new_session() as s:
            query = s.query(Display).filter(filter_)
            query = self._paginate(query, **list_params)
            return [self._from_db_format(row) for row in query.all()]

    def _build_filter(self, visible_tenants, display_uuid):
        if not visible_tenants and visible_tenants is not None:
            raise NoSuchDisplay(display_uuid)

        filter_ = Display.uuid == display_uuid
        if visible_tenants:
            filter_ = and_(filter_, Display.tenant_uuid.in_(visible_tenants))

        return filter_

    def _list_filter(self, visible_tenants, uuid=None, name=None, search=None, **list_params):
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

    def _paginate(self, query, limit=None, offset=None, order=None, direction=None, **ignored):
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
        return display.uuid

    @staticmethod
    def _from_db_format(display):
        columns = []
        for column in display.columns:
            d = {}
            if column.field is not None:
                d['field'] = column.field
            if column.title is not None:
                d['title'] = column.title
            if column.type is not None:
                d['type'] = column.type
            if column.number_display is not None:
                d['number_display'] = column.number_display
            if column.default is not None:
                d['default'] = column.default
            columns.append(d)

        return {
            'uuid': display.uuid,
            'tenant_uuid': display.tenant_uuid,
            'name': display.name,
            'columns': columns,
        }
