# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
from typing import TypedDict

from sqlalchemy import and_, exc, text
from wazo_dird.database.queries.base import Direction
from wazo_dird.exception import DuplicatedSourceException, NoSuchSource
from .base import BaseDAO
from .. import Source


class SourceBody(TypedDict, total=False):
    tenant_uuid: str
    name: str
    searched_columns: list[str]
    first_matched_columns: list[str]
    format_columns: dict[str, str]


class SourceCRUD(BaseDAO):
    _UNIQUE_CONSTRAINT_CODE = '23505'

    def count(self, backend: str, visible_tenants: list[str], **list_params):
        filter_ = self._list_filter(backend, visible_tenants, **list_params)
        with self.new_session() as s:
            return s.query(Source).filter(filter_).count()

    def list_(self, backend: str, visible_tenants: list[str], **list_params):
        filter_ = self._list_filter(backend, visible_tenants, **list_params)
        with self.new_session() as s:
            query = s.query(Source).filter(filter_)
            query = self._paginate(query, **list_params)
            return [self._from_db_format(row) for row in query.all()]

    def create(self, backend: str, source_body: SourceBody):
        with self.new_session() as s:
            self._create_tenant(s, source_body['tenant_uuid'])
            source = self._to_db_format(backend, **source_body)
            s.add(source)
            try:
                s.flush()
            except exc.IntegrityError as e:
                if e.orig.pgcode == self._UNIQUE_CONSTRAINT_CODE:
                    raise DuplicatedSourceException(source_body['name'])
                raise

            return self._from_db_format(source)

    def delete(self, backend: str, source_uuid: str, visible_tenants: list[str]):
        filter_ = self._multi_tenant_filter(backend, source_uuid, visible_tenants)
        with self.new_session() as s:
            nb_deleted = (
                s.query(Source).filter(filter_).delete(synchronize_session=False)
            )

        if not nb_deleted:
            raise NoSuchSource(source_uuid)

    def edit(
        self,
        backend: str,
        source_uuid: str,
        visible_tenants: list[str],
        body: SourceBody,
    ):
        filter_ = self._multi_tenant_filter(backend, source_uuid, visible_tenants)
        with self.new_session() as s:
            source = s.query(Source).filter(filter_).first()

            if not source:
                raise NoSuchSource(source_uuid)

            self._update_to_db_format(source, **body)
            try:
                s.flush()
            except exc.IntegrityError as e:
                if e.orig.pgcode == self._UNIQUE_CONSTRAINT_CODE:
                    raise DuplicatedSourceException(body['name'])
                raise

    def get(self, backend: str, source_uuid: str, visible_tenants: list[str]):
        filter_ = self._multi_tenant_filter(backend, source_uuid, visible_tenants)
        with self.new_session() as s:
            source = s.query(Source).filter(filter_).first()

            if not source:
                raise NoSuchSource(source_uuid)

            return self._from_db_format(source)

    def get_by_uuid(self, uuid: str):
        with self.new_session() as s:
            source = s.query(Source).filter(Source.uuid == uuid).first()

            if not source:
                raise NoSuchSource(uuid)

            return self._from_db_format(source)

    def _list_filter(
        self,
        backend: str,
        visible_tenants: list[str],
        uuid: str | None = None,
        name: str | None = None,
        search: str | None = None,
        **list_params,
    ):
        filter_ = text('true')
        if visible_tenants is not None:
            filter_ = and_(filter_, Source.tenant_uuid.in_(visible_tenants))
        if backend is not None:
            filter_ = and_(filter_, Source.backend == backend)
        if uuid is not None:
            filter_ = and_(filter_, Source.uuid == uuid)
        if name is not None:
            filter_ = and_(filter_, Source.name == name)
        if search is not None:
            pattern = f'%{search}%'
            filter_ = and_(filter_, Source.name.ilike(pattern))

        return filter_

    def _multi_tenant_filter(
        self, backend: str, source_uuid: str, visible_tenants: list[str]
    ):
        filter_ = and_(Source.backend == backend, Source.uuid == source_uuid)

        if visible_tenants is None:
            return filter_

        return and_(filter_, Source.tenant_uuid.in_(visible_tenants))

    def _paginate(
        self,
        query,
        limit: int | None = None,
        offset: int | None = None,
        order: str | None = None,
        direction: Direction | None = None,
        **ignored,
    ):
        if order and direction:
            field = None
            if order == 'name':
                field = Source.name
            if order == 'backend':
                field = Source.backend

            if field:
                order_clause = field.asc() if direction == 'asc' else field.desc()
                query = query.order_by(order_clause)

        if limit is not None:
            query = query.limit(limit)

        if offset is not None:
            query = query.offset(offset)

        return query

    def _to_db_format(
        self, backend: str, tenant_uuid: str, uuid: str | None = None, *args, **kwargs
    ):
        source = Source(uuid=uuid, backend=backend, tenant_uuid=tenant_uuid)
        return self._update_to_db_format(source, *args, **kwargs)

    @staticmethod
    def _update_to_db_format(
        source: Source,
        name: str,
        searched_columns: list[str],
        first_matched_columns: list[str],
        format_columns: dict[str, str],
        **extra_fields,
    ):
        source.name = name
        source.searched_columns = searched_columns
        source.first_matched_columns = first_matched_columns
        source.format_columns = format_columns
        source.extra_fields = extra_fields
        return source

    @staticmethod
    def _from_db_format(source: Source):
        return dict(
            uuid=source.uuid,
            backend=source.backend,
            name=source.name,
            tenant_uuid=source.tenant_uuid,
            searched_columns=source.searched_columns,
            first_matched_columns=source.first_matched_columns,
            format_columns=source.format_columns,
            **source.extra_fields or {},
        )
