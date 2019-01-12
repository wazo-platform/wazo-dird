# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os

from uuid import uuid4
from contextlib import closing
from hamcrest import (
    assert_that,
    contains,
    has_entries,
)
from .base_dird_integration_test import BasePhonebookTestCase
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from wazo_dird import database

Session = scoped_session(sessionmaker())
DB_URI_TPL = 'postgresql://asterisk:proformatique@localhost:{port}'


def new_uuid():
    return str(uuid4())


class TestTenantMigration(BasePhonebookTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        db_port = cls.service_port(5432, 'db')
        db_uri = os.getenv('DB_URI', DB_URI_TPL.format(port=db_port))
        engine = create_engine(db_uri)
        database.Base.metadata.bind = engine
        database.Base.metadata.reflect()
        database.Base.metadata.drop_all()
        database.Base.metadata.create_all()

    def test_tenant_uuid_migration(self):
        unknown_tenant_uuid = new_uuid()
        tenants = [
            {'name': 'foo', 'old_uuid': new_uuid(), 'new_uuid': new_uuid()},
            {'name': 'bar', 'old_uuid': new_uuid(), 'new_uuid': new_uuid()},
            {'name': 'unknown', 'old_uuid': unknown_tenant_uuid, 'new_uuid': unknown_tenant_uuid},
        ]

        with closing(Session()) as s:
            for tenant in tenants:
                s.add(database.Tenant(uuid=tenant['old_uuid'], name=tenant['name']))
            s.commit()

        for tenant in tenants:
            self.tenants[tenant['name']] = {'uuid': tenant['old_uuid']}

        self.set_tenants(tenants[0]['name'])
        phonebook_0 = self.post_phonebook(tenants[0]['name'], {'name': 'foo'}).json()

        self.set_tenants(tenants[1]['name'])
        phonebook_1 = self.post_phonebook(tenants[1]['name'], {'name': 'bar'}).json()

        self.set_tenants(tenants[2]['name'])
        phonebook_2 = self.post_phonebook(tenants[2]['name'], {'name': 'baz'}).json()

        body = [
            {'uuid': t['new_uuid'], 'name': t['name']}
            for t in tenants if t['name'] != 'unknown'
        ]
        body.append({'uuid': new_uuid(), 'name': 'ignored'})
        self.post_tenant_migration(body)

        for tenant in tenants:
            self.tenants[tenant['name']] = {'uuid': tenant['new_uuid']}

        self.set_tenants(tenants[0]['name'])
        assert_that(
            self.list_phonebooks(tenants[0]['name']).json(),
            has_entries(
                items=contains(phonebook_0),
                total=1,
            )
        )

        self.set_tenants(tenants[1]['name'])
        assert_that(
            self.list_phonebooks(tenants[1]['name']).json(),
            has_entries(
                items=contains(phonebook_1),
                total=1,
            )
        )

        self.set_tenants(tenants[2]['name'])
        assert_that(
            self.list_phonebooks(tenants[2]['name']).json(),
            has_entries(
                items=contains(phonebook_2),
                total=1,
            )
        )
