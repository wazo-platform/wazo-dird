# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import closing

from hamcrest import (
    assert_that,
    contains_exactly,
    contains_inanyorder,
    empty,
    equal_to,
    has_entries,
    has_items,
)

from wazo_dird import database

from .helpers.base import BaseDirdIntegrationTest
from .helpers.config import new_wazo_users_multiple_wazo_config
from .helpers.constants import MAIN_TENANT, USER_2_TOKEN, VALID_TOKEN_MAIN_TENANT

# See integration_tests/assets/confd_data/asset.wazo_users_multiple_wazo.
# The same confd id maps to a different uuid on each wazo, which is why the
# migration must build one mapping per source and not a global one.
AMERICA_USER_1_UUID = '7ca42f43-8bd9-4a26-acb8-cb756f42bebb'
AMERICA_USER_42_UUID = '696914c3-3698-42ef-9ee6-8efe30982f9c'
ASIA_USER_1_UUID = '7c12f90e-7391-4514-b482-5b75b57772e1'
EUROPE_USER_42_UUID = '8d0acfe6-054e-4d84-93c3-6d283937a7c9'

DELETED_USER_ID = '999'

# each wazo knows only its own users, so the seed favorite differs per source
SEED_UUIDS = {
    'wazo_america': AMERICA_USER_1_UUID,
    'wazo_america_sub': AMERICA_USER_1_UUID,
    'wazo_asia': ASIA_USER_1_UUID,
    'wazo_europe': EUROPE_USER_42_UUID,
}


class TestFavoriteMigration(BaseDirdIntegrationTest):
    asset = 'favorite_migration'
    config_factory = new_wazo_users_multiple_wazo_config

    def tearDown(self):
        with closing(self.Session()) as s:
            s.query(database.Favorite).delete()
            s.commit()
        self.configure_wazo_auth()
        super().tearDown()

    @classmethod
    def post_favorite_migration(cls, token=VALID_TOKEN_MAIN_TENANT):
        # the endpoint exists only while this asset enables the plugin
        return cls.post(cls.url('favorite_migration'), token=token)

    def _source_uuid(self, source_name):
        with closing(self.Session()) as s:
            source = (
                s.query(database.Source)
                .filter(database.Source.name == source_name)
                .first()
            )
            return source.uuid

    def _given_legacy_favorite(
        self, source_name, contact_id, token=VALID_TOKEN_MAIN_TENANT
    ):
        """Write the row a pre-upgrade wazo-dird would have written.

        It cannot go through the API: the write path now asks confd whether
        the contact exists, and a favorite kept by the migration may name a
        user confd no longer knows. The API call creates the dird_user row
        the favorite refers to, then the contact_id is forced.
        """
        seed_uuid = SEED_UUIDS[source_name]
        self.put_favorite(source_name, seed_uuid, token=token)
        source_uuid = self._source_uuid(source_name)
        with closing(self.Session()) as s:
            s.query(database.Favorite).filter(
                database.Favorite.source_uuid == source_uuid,
                database.Favorite.contact_id == seed_uuid,
            ).update({database.Favorite.contact_id: str(contact_id)})
            s.commit()

    def _contact_ids(self, source_name):
        source_uuid = self._source_uuid(source_name)
        with closing(self.Session()) as s:
            rows = (
                s.query(database.Favorite.contact_id)
                .filter(database.Favorite.source_uuid == source_uuid)
                .all()
            )
            return [row.contact_id for row in rows]

    def test_numeric_contact_id_becomes_the_user_uuid_of_its_own_source(self):
        self._given_legacy_favorite('wazo_america', '1')
        self._given_legacy_favorite('wazo_asia', '1')

        response = self.post_favorite_migration()
        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(migrated=2, already_migrated=0, dropped=0, failed_sources=0),
        )

        assert_that(
            self._contact_ids('wazo_america'), contains_exactly(AMERICA_USER_1_UUID)
        )
        assert_that(self._contact_ids('wazo_asia'), contains_exactly(ASIA_USER_1_UUID))

    def test_migration_is_idempotent(self):
        self._given_legacy_favorite('wazo_europe', '42')

        first = self.post_favorite_migration().json()
        assert_that(first, has_entries(migrated=1, already_migrated=0))

        second = self.post_favorite_migration().json()
        assert_that(second, has_entries(migrated=0, already_migrated=1, dropped=0))

        assert_that(
            self._contact_ids('wazo_europe'), contains_exactly(EUROPE_USER_42_UUID)
        )

    def test_unresolvable_contact_id_is_dropped_and_reported(self):
        # the code that follows this migration reads uuids only, so a favorite
        # naming no confd user cannot be left behind
        self._given_legacy_favorite('wazo_america', DELETED_USER_ID)

        report = self.post_favorite_migration().json()

        assert_that(report, has_entries(migrated=0, dropped=1))
        assert_that(
            report['sources'],
            has_items(
                has_entries(
                    source_name='wazo_america',
                    dropped=contains_exactly(has_entries(contact_id=DELETED_USER_ID)),
                )
            ),
        )
        assert_that(self._contact_ids('wazo_america'), empty())

    def test_row_colliding_with_an_existing_uuid_row_is_deduplicated(self):
        self.put_favorite('wazo_america', AMERICA_USER_42_UUID)
        source_uuid = self._source_uuid('wazo_america')
        with closing(self.Session()) as s:
            favorite = (
                s.query(database.Favorite)
                .filter(database.Favorite.source_uuid == source_uuid)
                .first()
            )
            s.add(
                database.Favorite(
                    source_uuid=source_uuid,
                    contact_id='42',
                    user_uuid=favorite.user_uuid,
                )
            )
            s.commit()

        assert_that(
            self._contact_ids('wazo_america'),
            contains_inanyorder(AMERICA_USER_42_UUID, '42'),
        )

        report = self.post_favorite_migration().json()

        assert_that(report, has_entries(migrated=0, deduplicated=1, dropped=0))
        assert_that(
            self._contact_ids('wazo_america'),
            contains_exactly(AMERICA_USER_42_UUID),
        )

    def test_migrated_favorites_are_listed_again(self):
        self._given_legacy_favorite('wazo_america', '1')

        self.post_favorite_migration()

        assert_that(
            self.favorites('default')['results'],
            contains_exactly(
                has_entries(
                    source='wazo_america',
                    column_values=contains_exactly('John', 'Doe', '1234'),
                    relations=has_entries(source_entry_id=AMERICA_USER_1_UUID),
                )
            ),
        )

    def test_favorites_of_a_source_whose_tenant_is_gone_are_dropped(self):
        self._given_legacy_favorite('wazo_america_sub', '1', token=USER_2_TOKEN)
        self.put_favorite('wazo_america_sub', AMERICA_USER_42_UUID, token=USER_2_TOKEN)
        self.mock_auth_client.set_tenants(
            {
                'uuid': MAIN_TENANT,
                'name': 'dird-tests-master',
                'parent_uuid': MAIN_TENANT,
            }
        )

        report = self.post_favorite_migration().json()

        assert_that(
            report,
            has_entries(migrated=0, dropped=2, orphan_sources=1, failed_sources=0),
        )
        assert_that(
            report['sources'],
            contains_exactly(
                has_entries(
                    source_name='wazo_america_sub',
                    tenant_deleted=True,
                    error=None,
                    dropped=contains_inanyorder(
                        has_entries(contact_id='1'),
                        has_entries(contact_id=AMERICA_USER_42_UUID),
                    ),
                )
            ),
        )
        assert_that(self._contact_ids('wazo_america_sub'), empty())

    def test_sources_without_favorites_are_not_queried(self):
        report = self.post_favorite_migration().json()

        assert_that(
            report,
            has_entries(
                migrated=0,
                already_migrated=0,
                dropped=0,
                failed_sources=0,
                sources=empty(),
            ),
        )
