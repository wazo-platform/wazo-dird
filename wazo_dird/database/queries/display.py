# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from sqlalchemy import and_
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

    def get(self, tenant_uuid, display_uuid):
        with self.new_session() as s:
            display = s.query(Display).filter(and_(
                Display.tenant_uuid == tenant_uuid,
                Display.uuid == display_uuid,
            )).first()

            columns = []
            for column in display.columns:
                d = {'name': column.name}
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
