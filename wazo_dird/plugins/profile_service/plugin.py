# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from wazo_dird import exception

from wazo_dird import (
    BaseServicePlugin,
    database,
)


class ProfileServicePlugin(BaseServicePlugin):

    def load(self, dependencies):
        self._config = dependencies['config']
        db_uri = self._config['db_uri']
        Session = self._new_db_session(db_uri)
        return _ProfileService(database.ProfileCRUD(Session))

    def _new_db_session(self, db_uri):
        self._Session = scoped_session(sessionmaker())
        engine = create_engine(db_uri)
        self._Session.configure(bind=engine)
        return self._Session


class _ProfileService:

    def __init__(self, crud):
        self._profile_crud = crud

    def get_by_name(self, tenant_uuid, name):
        for profile in self._profile_crud.list_([tenant_uuid], name=name):
            return profile

        raise exception.NoSuchProfile(name)

    def list_(self, visible_tenants, **list_params):
        return self._profile_crud.list_(visible_tenants, **list_params)
