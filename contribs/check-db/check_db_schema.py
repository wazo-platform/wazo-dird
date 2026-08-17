#!/usr/bin/env python3
# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fail if the models describe a schema that differs from the migrations.

Builds the schema two ways in two empty databases on the same server:

- "installed", from the models (`Base.metadata.create_all()`);
- "migrated", from the real migration chain (`alembic upgrade head`).

Then diffs the two live databases with `migra`. Both databases are stamped
to the same alembic revision first, so the version table itself never shows
up as a difference.

wazo-dird's migration chain has no earlier history to bootstrap: its root
revision (`down_revision = None`) executes the full baseline schema itself,
so `alembic upgrade head` from an empty database is already the complete
migrated schema. No separate baseline dump is needed here, unlike
`wazo-tools/compare-db`, which this script is modeled on.
"""
from __future__ import annotations

import argparse
import logging
import logging.config
import os
import sys

import sqlalchemy as sa
from migra import Migration
from sqlbag import S as sqlbag_session

from alembic import command as alembic_command  # type: ignore[attr-defined]
from alembic.config import Config as AlembicConfig
from wazo_dird.database import Base

LOGGER_NAME = 'check_db_schema'
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'default': {'format': '%(levelname)-5.5s [%(name)s] %(message)s'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'default'}},
    'loggers': {
        LOGGER_NAME: {'level': 'INFO', 'handlers': ['console'], 'propagate': False}
    },
}
log = logging.getLogger(LOGGER_NAME).info


def configure_logging() -> None:
    # alembic/env.py calls fileConfig(alembic.ini) on every alembic command
    # run here, which disables this logger since alembic.ini does not list
    # it; call this again after each alembic command to restore it.
    logging.config.dictConfig(LOGGING_CONFIG)


EXTENSIONS = ('uuid-ossp', 'unaccent', 'hstore')
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def main() -> int:
    configure_logging()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'server_uri',
        help=(
            'URI of a Postgres server with no database name, '
            'e.g. postgresql://postgres:postgres@localhost:5432'
        ),
    )
    args = parser.parse_args()

    installed_uri = f'{args.server_uri}/dird_installed'
    migrated_uri = f'{args.server_uri}/dird_migrated'

    log('Building the schema from the models...')
    build_installed_database(installed_uri)
    log('Building the schema from the migrations...')
    build_migrated_database(migrated_uri)

    log('Comparing the two schemas...')
    differences = compare(installed_uri, migrated_uri)

    if differences:
        log(
            'The models describe a schema that differs from the one the '
            'migrations install. Statements below would migrate the model '
            'schema to match the installed one; update the models '
            'to match instead of applying them:\n' + differences
        )
        return 1

    log('No difference found.')
    return 0


def build_installed_database(db_uri: str) -> None:
    reset_database(db_uri)
    engine = sa.create_engine(db_uri)
    try:
        Base.metadata.create_all(bind=engine)
    finally:
        engine.dispose()
    # No migration ever runs against this database, but it must be stamped
    # to the same revision as the migrated one so the version table itself
    # does not show up as a difference.
    alembic_command.stamp(build_alembic_config(db_uri), 'head')
    configure_logging()


def build_migrated_database(db_uri: str) -> None:
    reset_database(db_uri)
    alembic_command.upgrade(build_alembic_config(db_uri), 'head')
    configure_logging()


def reset_database(db_uri: str) -> None:
    server_uri, _, db_name = db_uri.rpartition('/')
    engine = sa.create_engine(f'{server_uri}/postgres', isolation_level='AUTOCOMMIT')
    try:
        with engine.connect() as connection:
            connection.execute(sa.text(f'DROP DATABASE IF EXISTS "{db_name}"'))
            connection.execute(sa.text(f'CREATE DATABASE "{db_name}"'))
    finally:
        engine.dispose()

    engine = sa.create_engine(db_uri, isolation_level='AUTOCOMMIT')
    try:
        with engine.connect() as connection:
            for extension in EXTENSIONS:
                connection.execute(
                    sa.text(f'CREATE EXTENSION IF NOT EXISTS "{extension}"')
                )
    finally:
        engine.dispose()


def build_alembic_config(db_uri: str) -> AlembicConfig:
    # env.py's run_migrations_online() reads this ahead of sqlalchemy.url.
    os.environ['ALEMBIC_DB_URI'] = db_uri
    alembic_cfg = AlembicConfig(os.path.join(REPO_ROOT, 'alembic.ini'))
    alembic_cfg.set_main_option('script_location', os.path.join(REPO_ROOT, 'alembic'))
    alembic_cfg.set_main_option('sqlalchemy.url', db_uri)
    return alembic_cfg


def compare(installed_uri: str, migrated_uri: str) -> str:
    with sqlbag_session(installed_uri) as installed, sqlbag_session(
        migrated_uri
    ) as migrated:
        migration = Migration(installed, migrated)
        migration.set_safety(False)
        migration.add_all_changes()
        return migration.sql


if __name__ == '__main__':
    sys.exit(main())
