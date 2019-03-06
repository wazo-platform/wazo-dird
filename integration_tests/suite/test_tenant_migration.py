# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from uuid import uuid4
from contextlib import closing
from hamcrest import (
    assert_that,
    contains,
    empty,
    has_entries,
)
from .base_dird_integration_test import BasePhonebookTestCase

from wazo_dird import database


def new_uuid():
    return str(uuid4())


class TestTenantMigration(BasePhonebookTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_tenant_uuid_migration(self):
        unknown_tenant_uuid = new_uuid()
        tenants = [
            {'name': 'foo', 'old_uuid': new_uuid(), 'new_uuid': new_uuid()},
            {'name': 'bar', 'old_uuid': new_uuid(), 'new_uuid': new_uuid()},
            # This tenant does not exist in wazo-auth
            {'name': 'unknown', 'old_uuid': unknown_tenant_uuid, 'new_uuid': unknown_tenant_uuid},
        ]

        # insert the old tenants in the dird DB
        with closing(self.Session()) as s:
            for tenant in tenants:
                s.add(database.Tenant(uuid=tenant['old_uuid'], name=tenant['name']))
            s.commit()

        # Pre-set the UUIDs in the base class to match the values in the DB
        for tenant in tenants:
            self.tenants[tenant['name']] = {'uuid': tenant['old_uuid']}

        # Create a phonebook in each tenants
        self.set_tenants(tenants[0]['name'])
        phonebook_0 = self.post_phonebook(tenants[0]['name'], {'name': 'foo'}).json()

        self.set_tenants(tenants[1]['name'])
        phonebook_1 = self.post_phonebook(tenants[1]['name'], {'name': 'bar'}).json()

        self.set_tenants(tenants[2]['name'])
        phonebook_2 = self.post_phonebook(tenants[2]['name'], {'name': 'baz'}).json()

        # Generate the POST body with the names and new UUIDS
        body = [
            {'uuid': t['new_uuid'], 'name': t['name']}
            for t in tenants if t['name'] != 'unknown'  # unknown does not exist in auth
        ]
        # Add an extra tenant that is not in wazo-dird
        body.append({'uuid': new_uuid(), 'name': 'ignored'})

        # Migrate all phonebooks from the old to the new UUIDs
        self.post_tenant_migration(body)

        # Set the new UUIDS in the test cache such that the auth mock returns the new UUIDs
        for tenant in tenants:
            self.tenants[tenant['name']] = {'uuid': tenant['new_uuid']}

        # wazo-auth now returns the new UUID and wazo-dird still return the matching phonebook
        self.set_tenants(tenants[0]['name'])
        assert_that(
            self.list_phonebooks(tenants[0]['name']).json(),
            has_entries(
                items=contains(has_entries(
                    id=phonebook_0['id'],
                    tenant_uuid=tenants[0]['new_uuid'],
                    name=phonebook_0['name'],
                    description=phonebook_0['description'],
                )),
                total=1,
            )
        )

        self.set_tenants(tenants[1]['name'])
        assert_that(
            self.list_phonebooks(tenants[1]['name']).json(),
            has_entries(
                items=contains(has_entries(
                    id=phonebook_1['id'],
                    tenant_uuid=tenants[1]['new_uuid'],
                    name=phonebook_1['name'],
                    description=phonebook_1['description'],
                )),
                total=1,
            )
        )

        self.set_tenants(tenants[2]['name'])
        assert_that(
            self.list_phonebooks(tenants[2]['name']).json(),
            has_entries(
                items=contains(has_entries(
                    id=phonebook_2['id'],
                    tenant_uuid=tenants[2]['new_uuid'],
                    name=phonebook_2['name'],
                    description=phonebook_2['description'],
                )),
                total=1,
            )
        )

        # check that migrated tenants are deleted
        with closing(self.Session()) as s:
            migrated_tenants = [t['old_uuid'] for t in tenants if t['name'] != 'unknown']
            matching_tenants = s.query(
                database.Tenant,
            ).filter(database.Tenant.uuid.in_(migrated_tenants)).all()
            assert_that(matching_tenants, empty())
