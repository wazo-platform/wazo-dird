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

    def delete(self, source_uuid, visible_tenants):
        filter_ = self._multi_tenant_filter(source_uuid, visible_tenants)
        with self.new_session() as s:
            nb_deleted = s.query(Source).filter(filter_).delete(synchronize_session=False)

        if not nb_deleted:
            raise NoSuchSource(source_uuid)

    def edit(self, source_uuid, visible_tenants, body):
        filter_ = self._multi_tenant_filter(source_uuid, visible_tenants)
        with self.new_session() as s:
            source = s.query(Source).filter(filter_).first()

            if not source:
                raise NoSuchSource(source_uuid)

            self._update_to_db_format(source, **body)

    def get(self, source_uuid, visible_tenants):
        filter_ = self._multi_tenant_filter(source_uuid, visible_tenants)
        with self.new_session() as s:
            source = s.query(Source).filter(filter_).first()

            if not source:
                raise NoSuchSource(source_uuid)

            return self._from_db_format(source)

    def _multi_tenant_filter(self, source_uuid, visible_tenants):
        return and_(
            Source.tenant_uuid.in_(visible_tenants),
            Source.uuid == source_uuid,
        )

    def _to_db_format(self, tenant_uuid, *args, **kwargs):
        source = Source(tenant_uuid=tenant_uuid)
        return self._update_to_db_format(source, *args, **kwargs)

    @staticmethod
    def _update_to_db_format(
            source,
            name,
            searched_columns,
            first_matched_columns,
            format_columns,
            **extra_fields
    ):
        source.name = name
        source.searched_columns = searched_columns
        source.first_matched_columns = first_matched_columns
        source.format_columns = format_columns
        source.extra_fields = extra_fields
        return source

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
