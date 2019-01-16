# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from sqlalchemy import and_
from wazo_dird.exception import NoSuchSource
from .base import BaseDAO
from ..import Source


class SourceCRUD(BaseDAO):

    def create(self, source_body):
        with self.new_session() as s:
            self._create_tenant(s, source_body['tenant_uuid'])
            source = self._to_db_format(**source_body)
            s.add(source)
            s.flush()
            return self._from_db_format(source)

    def get(self, tenant_uuid, source_uuid):
        with self.new_session() as s:
            source = s.query(Source).filter(and_(
                Source.tenant_uuid == tenant_uuid,
                Source.uuid == source_uuid,

            )).first()

            if not source:
                raise NoSuchSource(tenant_uuid, source_uuid)

            return self._from_db_format(source)

    @staticmethod
    def _to_db_format(
            name,
            tenant_uuid,
            searched_columns,
            first_matched_columns,
            format_columns,
            **extra_fields
    ):
        return Source(
            name=name,
            tenant_uuid=tenant_uuid,
            searched_columns=searched_columns,
            first_matched_columns=first_matched_columns,
            format_columns=format_columns,
            extra_fields=extra_fields,
        )

    @staticmethod
    def _from_db_format(source):
        return dict(
            uuid=source.uuid,
            name=source.name,
            tenant_uuid=source.tenant_uuid,
            searched_columns=source.searched_columns,
            first_matched_columns=source.first_matched_columns,
            format_columns=source.format_columns,
            **source.extra_fields
        )
