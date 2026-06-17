# Copyright 2015-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from time import time
from typing import Any

from xivo.rest_api_helpers import APIException


class OldAPIException(Exception):
    def __init__(self, status_code: int, body: dict[str, Any]) -> None:
        self.status_code = status_code
        self.body = body


class DatabaseServiceUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__('Postgresql is unavailable')


class NoSuchDisplay(APIException):  # type: ignore[misc]
    def __init__(self, uuid: Any) -> None:
        display_uuid = str(uuid)
        msg = f'No such display: "{display_uuid}"'
        details = {'uuid': display_uuid}
        super().__init__(404, msg, 'unknown-display', details, 'displays')


class NoSuchFavorite(ValueError):
    def __init__(self, contact_uuid: tuple[str, str]):
        message = f"No such favorite: {contact_uuid}"
        super().__init__(message)


class NoSuchPhonebook(ValueError):
    def __init__(
        self, phonebook_key: dict[str, Any], tenants_in_scope: list[str] | None = None
    ) -> None:
        if tenants_in_scope is None:
            message = f'No such phonebook: {phonebook_key}'
        else:
            message = (
                f'No such phonebook in tenants {tenants_in_scope}: {phonebook_key}'
            )
        super().__init__(message)


class NoSuchPhonebookAPIException(APIException):  # type: ignore[misc]
    def __init__(
        self, resource: str, visible_tenants: list[str], phonebook_key: dict[str, Any]
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


class PhonebookContactImportAPIError(APIException):  # type: ignore[misc]
    def __init__(
        self,
        message: str,
        error_id: str,
        details: dict[str, Any] | None = None,
        status_code: int = 400,
    ) -> None:
        super().__init__(
            status_code=status_code,
            message=message,
            error_id=error_id,
            details=details,
            resource='contacts',
        )


class NoSuchProfile(OldAPIException):
    def __init__(self, profile: Any) -> None:
        self.profile = profile
        status_code = 404
        body: dict[str, Any] = {
            'reason': [f'The profile `{profile}` does not exist'],
            'timestamp': [time()],
            'status_code': status_code,
        }
        super().__init__(status_code, body)


class NoSuchProfileAPIException(APIException):  # type: ignore[misc]
    def __init__(self, uuid: Any) -> None:
        profile_uuid = str(uuid)
        msg = f'No such profile: "{profile_uuid}"'
        details = {'uuid': profile_uuid}
        super().__init__(404, msg, 'unknown-profile', details, 'profiles')


class NoSuchUser(OldAPIException):
    def __init__(self, user_uuid: Any) -> None:
        status_code = 404
        body: dict[str, Any] = {
            'reason': [f'The user `{user_uuid}` does not exist'],
            'timestamp': [time()],
            'status_code': status_code,
        }
        super().__init__(status_code, body)


class NoSuchContact(ValueError):
    def __init__(self, contact_id: Any) -> None:
        message = f"No such contact: {contact_id}"
        super().__init__(message)


class NoSuchSource(APIException):  # type: ignore[misc]
    def __init__(self, uuid: Any) -> None:
        source_uuid = str(uuid)
        msg = f'No such source: "{source_uuid}"'
        details = {'uuid': source_uuid}
        super().__init__(404, msg, 'unknown-source', details, 'sources')


class NoSuchTenant(ValueError):
    def __init__(self, tenant_name: Any) -> None:
        message = f'No such tenant: {tenant_name}'
        super().__init__(message)


class DuplicatedContactException(Exception):
    _msg = 'Duplicate contact'

    def __init__(self) -> None:
        super().__init__(self._msg)


class ContactCreationError(Exception):
    def __init__(self, msg: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(msg)
        self.details = details or {}


class ContactUpdateError(Exception):
    def __init__(self, msg: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(msg)
        self.details = details or {}


class DuplicatedFavoriteException(Exception):
    pass


class DuplicatedPhonebookException(Exception):
    _msg = 'Duplicating phonebook'

    def __init__(self) -> None:
        super().__init__(self._msg)


class PhonebookCreationError(Exception):
    def __init__(self, msg: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(msg)
        self.details = details or {}


class PhonebookUpdateError(Exception):
    def __init__(self, msg: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(msg)
        self.details = details or {}


class DuplicatedProfileException(APIException):  # type: ignore[misc]
    def __init__(self, name: Any) -> None:
        msg = f'The name "{name}" is already used'
        details = {'name': {'constraint_id': 'unique', 'message': msg}}
        super().__init__(409, 'Conflict detected', 'conflict', details, 'profiles')


class DuplicatedSourceException(APIException):  # type: ignore[misc]
    def __init__(self, name: Any) -> None:
        msg = f'The name "{name}" is already used'
        details = {'name': {'constraint_id': 'unique', 'message': msg}}
        super().__init__(409, 'Conflict detected', 'conflict', details, 'sources')


class ProfileNotFoundError(Exception):
    pass


class InvalidArgumentError(Exception):
    pass


class InvalidConfigError(Exception):
    def __init__(self, location_path: str, msg: str) -> None:
        super().__init__(f'{location_path}: {msg}')
        self.location_path = location_path
        self.msg = msg


class InvalidSourceConfigError(InvalidConfigError):
    def __init__(
        self,
        source_info: dict[str, Any],
        details: dict[str, Any] | None = None,
        details_fmt: str = '',
    ) -> None:
        assert 'backend' in source_info, repr(source_info)
        super().__init__(
            location_path=f'/backends/{source_info["backend"]}/sources',
            msg=(
                f'Invalid config for source(name={source_info.get("name")})'
                + (f': {details_fmt.format_map(details or {})}' if details_fmt else '')
            ),
        )
        self.source_info = source_info
        self.details = details


class InvalidSourceConfigAPIError(APIException):  # type: ignore[misc]
    def __init__(
        self, source_info: dict[str, Any], details: dict[str, Any] | None = None
    ) -> None:
        details = details or {}
        details.update(source_info=source_info)
        super().__init__(
            400, 'Invalid source config', 'invalid-source-config', details, 'sources'
        )


class InvalidPhonebookException(Exception):
    def __init__(self, errors: Any) -> None:
        self.errors = errors

    def __str__(self) -> str:
        return str(self.errors)


class InvalidContactException(Exception):
    pass


class WazoConfdError(APIException):  # type: ignore[misc]
    def __init__(self, confd_client: Any, error: Exception) -> None:
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


class MasterTenantNotInitiatedException(APIException):  # type: ignore[misc]
    def __init__(self) -> None:
        error_message = 'wazo-dird master tenant is not initiated'
        super().__init__(503, error_message, 'matser-tenant-not-initiated')
