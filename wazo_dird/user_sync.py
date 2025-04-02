# Copyright 2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import logging
import sys

from xivo import xivo_logging
from xivo.user_rights import change_user

from wazo_dird import database
from wazo_dird.config import load as load_config
from wazo_dird.database.helpers import Session, init_db

logger = logging.getLogger(__name__)


def sync_user(data: dict) -> None:
    if not data.get('uuid') or not data.get('tenant_uuid'):
        raise ValueError("Missing `uuid` or `tenant_uuid`")

    session = Session()

    tenant = (
        session.query(database.Tenant)
        .filter(database.Tenant.uuid == data['tenant_uuid'])
        .first()
    )
    if not tenant:
        tenant = database.Tenant(uuid=data['tenant_uuid'])

    if country := data.get('country'):
        tenant.country = country

    session.add(tenant)
    session.flush()

    user = (
        session.query(database.User)
        .filter(database.User.user_uuid == data['uuid'])
        .first()
    )
    if not user:
        user = database.User(user_uuid=data['uuid'])

    user.tenant_uuid = data['tenant_uuid']
    session.add(user)
    session.flush()

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        Session.remove()


def sync_users(json_data: str) -> None:
    """Expects a JSON string with the minimum format:
    [{"uuid":"...","tenant_uuid":"..."}, ...]
    """
    users = json.loads(json_data)
    if not isinstance(users, list):
        raise ValueError("Users should be a list")

    for user in users:
        try:
            sync_user(user)
        except ValueError:
            logger.error('Error while reading user "%s"', user, exc_info=True)
            continue


def main(argv=None) -> None:
    argv = argv or sys.argv[1:]

    config = load_config(argv)

    xivo_logging.setup_logging(
        config['log_filename'],
        debug=config['debug'],
        log_level=config['log_level'],
    )

    if config['user']:
        change_user(config['user'])

    init_db(config['db_uri'], pool_size=config['rest_api']['max_threads'])

    if not sys.stdin.readable():
        print("Please provide data in stdin")
        return

    sync_users(sys.stdin.read())
