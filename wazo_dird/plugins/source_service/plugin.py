# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from wazo_dird import (
    BaseServicePlugin,
    database,
)


class SourceServicePlugin(BaseServicePlugin):

    def load(self, dependencies):
        self._config = dependencies['config']
        db_uri = self._config['db_uri']
        Session = self._new_db_session(db_uri)
        return _SourceService(database.SourceCRUD(Session))

    def _new_db_session(self, db_uri):
        self._Session = scoped_session(sessionmaker())
        engine = create_engine(db_uri)
        self._Session.configure(bind=engine)
        return self._Session


class _SourceService:

    def __init__(self, crud):
        self._source_crud = crud

    def count(self, visible_tenants, **list_params):
        return self._source_crud.count(visible_tenants, **list_params)

    def create(self, **body):
        return self._source_crud.create(body)

    def delete(self, source_uuid, visible_tenants):
        return self._source_crud.delete(source_uuid, visible_tenants)

    def edit(self, source_uuid, visible_tenants, body):
        return self._source_crud.edit(source_uuid, visible_tenants, body)

    def get(self, source_uuid, visible_tenants):
        return self._source_crud.get(source_uuid, visible_tenants)

    def list_(self, visible_tenants, **list_params):
        return self._source_crud.list_(visible_tenants, **list_params)
