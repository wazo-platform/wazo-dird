# Copyright 2015-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from collections.abc import Callable
from typing import TypeVar

from wazo_auth_client import Client
from werkzeug.local import LocalProxy as Proxy
from xivo.auth_verifier import no_auth, required_acl, required_tenant
from xivo.status import Status

from .exception import MasterTenantNotInitiatedException
from .http_server import app

logger = logging.getLogger(__name__)

auth_config = None
auth_client = None


def set_auth_config(config):
    global auth_config
    auth_config = config


def client():
    global auth_client
    if not auth_client:
        auth_client = Client(**auth_config)
    return auth_client


F = TypeVar('F', bound=Callable)
Decorator = Callable[[F], F]


def required_master_tenant() -> Decorator:
    return required_tenant(master_tenant_uuid)


def init_master_tenant(token):
    tenant_uuid = token['metadata']['tenant_uuid']
    app.config['auth']['master_tenant_uuid'] = tenant_uuid


def provide_status(status):
    status['master_tenant']['status'] = (
        Status.ok if app.config['auth'].get('master_tenant_uuid') else Status.fail
    )


def get_master_tenant_uuid():
    if not app:
        raise Exception('Flask application is not configured')

    tenant_uuid = app.config['auth'].get('master_tenant_uuid')
    if not tenant_uuid:
        raise MasterTenantNotInitiatedException()

    return tenant_uuid


master_tenant_uuid = Proxy(get_master_tenant_uuid)
__all__ = ['required_acl', 'no_auth']
