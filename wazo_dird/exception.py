# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from time import time

from xivo.rest_api_helpers import APIException


class OldAPIException(Exception):
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body


class DatabaseServiceUnavailable(Exception):
    def __init__(self):
        super().__init__('Postgresql is unavailable')


class NoSuchDisplay(APIException):
    def __init__(self, uuid):
        display_uuid = str(uuid)
        msg = f'No such display: "{display_uuid}"'
        details = {'uuid': display_uuid}
        super().__init__(404, msg, 'unknown-display', details, 'displays')


class NoSuchFavorite(ValueError):
    def __init__(self, contact_uuid: str):
        message = f"No such favorite: {contact_uuid}"
        super().__init__(message)


class NoSuchPhonebook(ValueError):
    def __init__(self, phonebook_key: dict, tenants_in_scope: list[str] | None = None):
        if tenants_in_scope is None:
            message = f'No such phonebook: {phonebook_key}'
        else:
            message = (
                f'No such phonebook in tenants {tenants_in_scope}: {phonebook_key}'
            )
        super().__init__(message)


class NoSuchPhonebookAPIException(APIException):
    def __init__(
        self, resource: str, visible_tenants: list[str], phonebook_key: dict
    ) -> None:
        super().__init__(
            status_code=404,
            message=f'Phonebook {phonebook_key} not found in tenants {visible_tenants}',
            error_id='unknown-phonebook',
            details={
                'phonebook_key': phonebook_key,
                'visible_tenants': visible_tenants,
            },
            resource=resource,
        )


class NoSuchProfile(OldAPIException):
    def __init__(self, profile):
        self.profile = profile
        status_code = 404
        body = {
            'reason': [f'The profile `{profile}` does not exist'],
            'timestamp': [time()],
            'status_code': status_code,
        }
        super().__init__(status_code, body)


class NoSuchProfileAPIException(APIException):
    def __init__(self, uuid):
        profile_uuid = str(uuid)
        msg = f'No such profile: "{profile_uuid}"'
        details = {'uuid': profile_uuid}
        super().__init__(404, msg, 'unknown-profile', details, 'profiles')


class NoSuchUser(OldAPIException):
    def __init__(self, user_uuid):
        status_code = 404
        body = {
            'reason': [f'The user `{user_uuid}` does not exist'],
            'timestamp': [time()],
            'status_code': status_code,
        }
        super().__init__(status_code, body)


class NoSuchContact(ValueError):
    def __init__(self, contact_id):
        message = f"No such contact: {contact_id}"
        super().__init__(message)


class NoSuchSource(APIException):
    def __init__(self, uuid):
        source_uuid = str(uuid)
        msg = f'No such source: "{source_uuid}"'
        details = {'uuid': source_uuid}
        super().__init__(404, msg, 'unknown-source', details, 'sources')


class NoSuchTenant(ValueError):
    def __init__(self, tenant_name):
        message = f'No such tenant: {tenant_name}'
        super().__init__(message)


class DuplicatedContactException(Exception):
    _msg = 'Duplicating contact'

    def __init__(self):
        super().__init__(self._msg)


class DuplicatedFavoriteException(Exception):
    pass


class DuplicatedPhonebookException(Exception):
    _msg = 'Duplicating phonebook'

    def __init__(self):
        super().__init__(self._msg)


class DuplicatedProfileException(APIException):
    def __init__(self, name):
        msg = f'The name "{name}" is already used'
        details = {'name': {'constraint_id': 'unique', 'message': msg}}
        super().__init__(409, 'Conflict detected', 'conflict', details, 'profiles')


class DuplicatedSourceException(APIException):
    def __init__(self, name):
        msg = f'The name "{name}" is already used'
        details = {'name': {'constraint_id': 'unique', 'message': msg}}
        super().__init__(409, 'Conflict detected', 'conflict', details, 'sources')


class ProfileNotFoundError(Exception):
    pass


class InvalidArgumentError(Exception):
    pass


class InvalidConfigError(Exception):
    def __init__(self, location_path, msg):
        super().__init__(f'{location_path}: {msg}')
        self.location_path = location_path
        self.msg = msg


class InvalidSourceConfigError(InvalidConfigError):
    def __init__(
        self, source_info: dict, details: dict | None = None, details_fmt: str = ''
    ):
        assert 'backend' in source_info, repr(source_info)
        super().__init__(
            location_path=f'/backends/{source_info["backend"]}/sources',
            msg=(
                f'Invalid config for source(name={source_info["name"]})'
                + (f': {details_fmt.format_map(details or {})}' if details_fmt else '')
            ),
        )
        self.source_info = source_info
        self.details = details


class InvalidSourceConfigAPIError(APIException):
    def __init__(self, source_info: dict, details: dict | None = None) -> None:
        details = details or {}
        details.update(source_info=source_info)
        super().__init__(
            400, 'Invalid source config', 'invalid-source-config', details, 'sources'
        )


class InvalidPhonebookException(Exception):
    def __init__(self, errors):
        self.errors = errors

    def __str__(self):
        return str(self.errors)


class InvalidContactException(Exception):
    pass


class WazoConfdError(APIException):
    def __init__(self, confd_client, error):
        super().__init__(
            status_code=503,
            message='wazo-confd request error',
            error_id='wazo-confd-error',
            details={
                'wazo_confd_config': {
                    'host': confd_client.host,
                    'port': confd_client.port,
                    'timeout': confd_client.timeout,
                },
                'original_error': str(error),
            },
        )


class MasterTenantNotInitiatedException(APIException):
    def __init__(self):
        error_message = 'wazo-dird master tenant is not initiated'
        super().__init__(503, error_message, 'matser-tenant-not-initiated')
