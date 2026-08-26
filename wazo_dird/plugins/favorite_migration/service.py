# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from typing import Any, Protocol, TypedDict

from requests.exceptions import RequestException
from sqlalchemy import and_

from wazo_dird.database import Favorite
from wazo_dird.database.helpers import Session
from wazo_dird.database.queries.base import BaseDAO
from wazo_dird.database.queries.source import SourceInfo
from wazo_dird.plugin_helpers.confd_client_registry import registry
from wazo_dird.utils import is_uuid

logger = logging.getLogger(__name__)

BACKEND = 'wazo'


class SourceServiceProtocol(Protocol):
    def list_(
        self, backend: str, visible_tenants: list[str] | None, **list_params: Any
    ) -> list[SourceInfo]:
        ...


class DroppedFavorite(TypedDict):
    contact_id: str
    user_uuid: str


class SourceReport(TypedDict):
    source_uuid: str
    source_name: str
    migrated: int
    already_migrated: int
    deduplicated: int
    dropped: list[DroppedFavorite]
    error: str | None


class MigrationReport(TypedDict):
    migrated: int
    already_migrated: int
    deduplicated: int
    dropped: int
    failed_sources: int
    sources: list[SourceReport]


class FavoriteMigrationDAO(BaseDAO):
    def list_favorites(self, source_uuid: str) -> list[tuple[str, str]]:
        with self.new_session() as s:
            rows = (
                s.query(Favorite.contact_id, Favorite.user_uuid)
                .filter(Favorite.source_uuid == source_uuid)
                .all()
            )
            return [(row.contact_id, row.user_uuid) for row in rows]

    def drop(self, source_uuid: str, favorites: list[tuple[str, str]]) -> int:
        """Delete favorites of one source, by (user_uuid, contact_id) pairs."""
        if not favorites:
            return 0

        with self.new_session() as s:
            for user_uuid, contact_id in favorites:
                s.query(Favorite).filter(
                    and_(
                        Favorite.source_uuid == source_uuid,
                        Favorite.user_uuid == user_uuid,
                        Favorite.contact_id == contact_id,
                    )
                ).delete(synchronize_session=False)

        return len(favorites)

    def migrate(
        self, source_uuid: str, changes: list[tuple[str, str, str]]
    ) -> tuple[int, int]:
        """Rewrite contact_ids of one source in a single transaction.

        `changes` holds (user_uuid, old_contact_id, new_contact_id) triples.
        Returns the number of rows updated and the number dropped because the
        target row already existed.
        """
        if not changes:
            return 0, 0

        migrated = 0
        deduplicated = 0
        with self.new_session() as s:
            for user_uuid, old_contact_id, new_contact_id in changes:
                old_filter = and_(
                    Favorite.source_uuid == source_uuid,
                    Favorite.user_uuid == user_uuid,
                    Favorite.contact_id == old_contact_id,
                )
                new_filter = and_(
                    Favorite.source_uuid == source_uuid,
                    Favorite.user_uuid == user_uuid,
                    Favorite.contact_id == new_contact_id,
                )
                if s.query(Favorite).filter(new_filter).count():
                    s.query(Favorite).filter(old_filter).delete(
                        synchronize_session=False
                    )
                    deduplicated += 1
                else:
                    s.query(Favorite).filter(old_filter).update(
                        {Favorite.contact_id: new_contact_id},
                        synchronize_session=False,
                    )
                    migrated += 1

        return migrated, deduplicated


class FavoriteMigrationService:
    def __init__(self, source_service: SourceServiceProtocol) -> None:
        self._source_service = source_service
        self._dao = FavoriteMigrationDAO(Session)

    def migrate(self) -> MigrationReport:
        report: MigrationReport = {
            'migrated': 0,
            'already_migrated': 0,
            'deduplicated': 0,
            'dropped': 0,
            'failed_sources': 0,
            'sources': [],
        }

        for source in self._source_service.list_(BACKEND, None):
            source_report = self._migrate_source(source)
            if source_report is None:
                continue
            report['sources'].append(source_report)
            report['migrated'] += source_report['migrated']
            report['already_migrated'] += source_report['already_migrated']
            report['deduplicated'] += source_report['deduplicated']
            report['dropped'] += len(source_report['dropped'])
            if source_report['error']:
                report['failed_sources'] += 1

        logger.info('favorite migration done: %s', report)
        return report

    def _migrate_source(self, source: SourceInfo) -> SourceReport | None:
        source_uuid = source['uuid']
        favorites = self._dao.list_favorites(source_uuid)
        if not favorites:
            return None

        report: SourceReport = {
            'source_uuid': source_uuid,
            'source_name': source['name'],
            'migrated': 0,
            'already_migrated': 0,
            'deduplicated': 0,
            'dropped': [],
            'error': None,
        }

        pending = [
            (contact_id, user_uuid)
            for contact_id, user_uuid in favorites
            if not is_uuid(contact_id)
        ]
        report['already_migrated'] = len(favorites) - len(pending)
        if not pending:
            return report

        try:
            id_to_uuid = self._fetch_id_to_uuid(source)
        except (RequestException, KeyError) as e:
            logger.warning(
                'source %s: cannot fetch confd users, skipping: %s', source['name'], e
            )
            report['error'] = str(e)
            return report

        changes: list[tuple[str, str, str]] = []
        drops: list[tuple[str, str]] = []
        for contact_id, user_uuid in pending:
            new_contact_id = id_to_uuid.get(contact_id)
            if not new_contact_id:
                # the code that follows this migration reads uuids only, so a
                # favorite naming no confd user is dropped rather than kept as
                # a row nothing can resolve
                logger.warning(
                    'source %s: favorite %s of user %s matches no confd user, dropping it',
                    source['name'],
                    contact_id,
                    user_uuid,
                )
                report['dropped'].append(
                    {'contact_id': contact_id, 'user_uuid': user_uuid}
                )
                drops.append((user_uuid, contact_id))
                continue
            changes.append((user_uuid, contact_id, new_contact_id))

        report['migrated'], report['deduplicated'] = self._dao.migrate(
            source_uuid, changes
        )
        self._dao.drop(source_uuid, drops)
        return report

    def _fetch_id_to_uuid(self, source: SourceInfo) -> dict[str, str]:
        client = registry.get(source)
        users = client.users.list(view='directory', recurse=True)
        logger.info('source %s: fetched %s confd users', source['name'], users['total'])
        return {str(user['id']): user['uuid'] for user in users['items']}
