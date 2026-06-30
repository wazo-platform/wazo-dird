# Copyright 2016-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import csv
import logging
import time
from collections.abc import Callable, Mapping, Sequence
from functools import wraps
from typing import TYPE_CHECKING, Any, TypedDict, TypeVar

from flask import request
from wazo_auth_client import Client as AuthClient
from xivo.tenant_flask_helpers import Tenant

from wazo_dird.auth import required_acl
from wazo_dird.exception import (
    DatabaseServiceUnavailable,
    DuplicatedContactException,
    DuplicatedPhonebookException,
    InvalidArgumentError,
    InvalidContactException,
    InvalidPhonebookException,
    NoSuchContact,
    NoSuchPhonebook,
    NoSuchTenant,
)
from wazo_dird.http import LegacyAuthResource, get_json_body

if TYPE_CHECKING:
    from wazo_dird.plugins.phonebook_service.plugin import _PhonebookService

logger = logging.getLogger(__name__)

R = TypeVar('R')

ErrorResponse = tuple[dict[str, Any], int]
Response = tuple[Any, int] | dict[str, Any]


def _make_error(reason: str, status_code: int) -> ErrorResponse:
    return (
        {'reason': [reason], 'timestamp': [time.time()], 'status_code': status_code},
        status_code,
    )


class _Resource(LegacyAuthResource):
    error_code_map: dict[type[Exception], int] = {}

    def __init__(
        self, phonebook_service: _PhonebookService, auth_client: AuthClient
    ) -> None:
        self.phonebook_service = phonebook_service
        self._auth_client: AuthClient = auth_client

    def _find_tenant(self, scoping_tenant: Tenant, name: str) -> dict[str, Any]:
        tenants = self._auth_client.tenants.list(
            tenant_uuid=scoping_tenant.uuid, name=name
        )['items']
        for tenant in tenants:
            tenant_dict: dict[str, Any] = tenant
            return tenant_dict
        raise NoSuchTenant(name)


class _ArgParser:
    def __init__(
        self, args: Mapping[str, str], valid_columns: list[str] | None = None
    ) -> None:
        self._search = args.get('search')
        self._direction = self._get_string_from_valid_values(
            args, 'direction', ['asc', 'desc', None]
        )
        self._limit = self._get_positive_int(args, 'limit')
        self._offset = self._get_positive_int(args, 'offset')
        self._order = self._get_string_from_valid_values(args, 'order', valid_columns)

    def count_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if self._search:
            params['search'] = self._search
        return params

    def list_params(self) -> dict[str, Any]:
        params = self.count_params()
        if self._direction:
            params['direction'] = self._direction
        if self._order:
            params['order'] = self._order
        if self._limit:
            params['limit'] = self._limit
        if self._offset:
            params['offset'] = self._offset
        return params

    @staticmethod
    def _get_string_from_valid_values(
        args: Mapping[str, str], name: str, valid_values: Sequence[str | None] | None
    ) -> str | None:
        if name not in args:
            return None

        value = args.get(name)
        if valid_values is None:
            return value

        if value in valid_values:
            return value

        raise InvalidArgumentError(f'{name} should be one of {valid_values}')

    @staticmethod
    def _get_positive_int(args: Mapping[str, str], name: str) -> int:
        try:
            value = int(args.get(name, 0))
            if value >= 0:
                return value
        except ValueError:
            pass

        raise InvalidArgumentError(f'{name} should be a positive integer')


def _default_error_route(
    f: Callable[..., R],
) -> Callable[..., R | ErrorResponse]:
    @wraps(f)
    def decorator(self_: _Resource, *args: Any, **kwargs: Any) -> R | ErrorResponse:
        try:
            return f(self_, *args, **kwargs)
        except tuple(self_.error_code_map.keys()) as e:
            logger.info('%s', e)
            code = self_.error_code_map[e.__class__]
            return _make_error(str(e), code)

    return decorator


class PhonebookKey(TypedDict, total=False):
    id: int
    uuid: str


def deprecated_endpoint(endpoint_func: Callable[..., R]) -> Callable[..., R]:
    @wraps(endpoint_func)
    def wrapper(self: _Resource, *args: Any, **kwargs: Any) -> R:
        endpoint_name = endpoint_func.__name__
        endpoint_context = self.__class__.__name__
        logger.warning(
            f"Endpoint {endpoint_context}.{endpoint_name} is deprecated. "
            "This endpoint will be removed in a future release. "
            "Please consider switching to an alternative endpoint."
        )
        return endpoint_func(self, *args, **kwargs)

    return wrapper


class DeprecatedPhonebookContactAll(_Resource):
    error_code_map = {
        InvalidArgumentError: 400,
        InvalidContactException: 400,
        NoSuchPhonebook: 404,
        DatabaseServiceUnavailable: 503,
        DuplicatedContactException: 409,
        NoSuchTenant: 404,
    }

    @deprecated_endpoint
    @required_acl('dird.tenants.{tenant}.phonebooks.{phonebook_id}.contacts.create')
    @_default_error_route
    def post(self, tenant: str, phonebook_id: int) -> Response:
        scoping_tenant = Tenant.autodetect()
        matching_tenant = self._find_tenant(scoping_tenant, tenant)
        return (
            self.phonebook_service.create_contact(
                [matching_tenant['uuid']],
                PhonebookKey(id=phonebook_id),
                get_json_body(),
            ),
            201,
        )

    @deprecated_endpoint
    @required_acl('dird.tenants.{tenant}.phonebooks.{phonebook_id}.contacts.read')
    @_default_error_route
    def get(self, tenant: str, phonebook_id: int) -> Response:
        parser = _ArgParser(request.args)
        scoping_tenant = Tenant.autodetect()
        matching_tenant = self._find_tenant(scoping_tenant, tenant)
        count = self.phonebook_service.count_contact(
            [matching_tenant['uuid']],
            PhonebookKey(id=phonebook_id),
            **parser.count_params(),
        )
        contacts = self.phonebook_service.list_contacts(
            [matching_tenant['uuid']],
            PhonebookKey(id=phonebook_id),
            **parser.list_params(),
        )

        return {'items': contacts, 'total': count}, 200


class DeprecatedPhonebookAll(_Resource):
    error_code_map = {
        InvalidArgumentError: 400,
        DuplicatedPhonebookException: 409,
        DatabaseServiceUnavailable: 503,
        InvalidPhonebookException: 400,
        NoSuchTenant: 404,
    }

    @deprecated_endpoint
    @required_acl('dird.tenants.{tenant}.phonebooks.read')
    @_default_error_route
    def get(self, tenant: str) -> Response:
        scoping_tenant = Tenant.autodetect()
        matching_tenant = self._find_tenant(scoping_tenant, tenant)
        parser = _ArgParser(request.args, valid_columns=['name', 'description'])

        count = self.phonebook_service.count_phonebook(
            [matching_tenant['uuid']], **parser.count_params()
        )
        phonebooks = self.phonebook_service.list_phonebook(
            [matching_tenant['uuid']], **parser.list_params()
        )

        return {'items': phonebooks, 'total': count}

    @deprecated_endpoint
    @required_acl('dird.tenants.{tenant}.phonebooks.create')
    @_default_error_route
    def post(self, tenant: str) -> Response:
        scoping_tenant = Tenant.autodetect()
        matching_tenant = self._find_tenant(scoping_tenant, tenant)
        return (
            self.phonebook_service.create_phonebook(
                matching_tenant['uuid'], get_json_body()
            ),
            201,
        )


class DeprecatedPhonebookContactImport(_Resource):
    error_code_map = {NoSuchTenant: 404, NoSuchPhonebook: 404}

    @deprecated_endpoint
    @required_acl('dird.tenants.{tenant}.phonebooks.{phonebook_id}.contacts.create')
    @_default_error_route
    def post(self, tenant: str, phonebook_id: int) -> Response:
        scoping_tenant = Tenant.autodetect()
        matching_tenant = self._find_tenant(scoping_tenant, tenant)
        charset = request.mimetype_params.get('charset', 'utf-8')
        try:
            data = request.data.decode(charset).split('\n')
        except LookupError as e:
            if 'unknown encoding:' in str(e):
                return _make_error(str(e), 400)
            else:
                raise

        reader = csv.reader(data)
        fields = next(reader)
        duplicates = list({f for f in fields if fields.count(f) > 1})
        if duplicates:
            return _make_error(f'duplicate columns: {duplicates}', 400)

        to_add = [c for c in csv.DictReader(data)]
        created, failed = self.phonebook_service.import_contacts(
            [matching_tenant['uuid']], PhonebookKey(id=phonebook_id), to_add
        )

        return {'created': created, 'failed': failed}


class DeprecatedPhonebookContactOne(_Resource):
    error_code_map = {
        DuplicatedContactException: 409,
        InvalidContactException: 400,
        DatabaseServiceUnavailable: 503,
        NoSuchContact: 404,
        NoSuchPhonebook: 404,
        NoSuchTenant: 404,
    }

    @deprecated_endpoint
    @required_acl(
        'dird.tenants.{tenant}.phonebooks.{phonebook_id}.contacts.{contact_uuid}.read'
    )
    @_default_error_route
    def get(self, tenant: str, phonebook_id: int, contact_uuid: str) -> Response:
        scoping_tenant = Tenant.autodetect()
        matching_tenant = self._find_tenant(scoping_tenant, tenant)
        return (
            self.phonebook_service.get_contact(
                [matching_tenant['uuid']], PhonebookKey(id=phonebook_id), contact_uuid
            ),
            200,
        )

    @deprecated_endpoint
    @required_acl(
        'dird.tenants.{tenant}.phonebooks.{phonebook_id}.contacts.{contact_uuid}.delete'
    )
    @_default_error_route
    def delete(self, tenant: str, phonebook_id: int, contact_uuid: str) -> Response:
        scoping_tenant = Tenant.autodetect()
        matching_tenant = self._find_tenant(scoping_tenant, tenant)
        self.phonebook_service.delete_contact(
            [matching_tenant['uuid']], PhonebookKey(id=phonebook_id), contact_uuid
        )
        return '', 204

    @deprecated_endpoint
    @required_acl(
        'dird.tenants.{tenant}.phonebooks.{phonebook_id}.contacts.{contact_uuid}.update'
    )
    @_default_error_route
    def put(self, tenant: str, phonebook_id: int, contact_uuid: str) -> Response:
        scoping_tenant = Tenant.autodetect()
        matching_tenant = self._find_tenant(scoping_tenant, tenant)
        return (
            self.phonebook_service.edit_contact(
                [matching_tenant['uuid']],
                PhonebookKey(id=phonebook_id),
                contact_uuid,
                get_json_body(),
            ),
            200,
        )


class DeprecatedPhonebookOne(_Resource):
    error_code_map = {
        DatabaseServiceUnavailable: 503,
        DuplicatedPhonebookException: 409,
        InvalidPhonebookException: 400,
        NoSuchPhonebook: 404,
        NoSuchTenant: 404,
    }

    @deprecated_endpoint
    @required_acl('dird.tenants.{tenant}.phonebooks.{phonebook_id}.delete')
    @_default_error_route
    def delete(self, tenant: str, phonebook_id: int) -> Response:
        scoping_tenant = Tenant.autodetect()
        matching_tenant = self._find_tenant(scoping_tenant, tenant)
        self.phonebook_service.delete_phonebook(
            [matching_tenant['uuid']], PhonebookKey(id=phonebook_id)
        )
        return '', 204

    @deprecated_endpoint
    @required_acl('dird.tenants.{tenant}.phonebooks.{phonebook_id}.read')
    @_default_error_route
    def get(self, tenant: str, phonebook_id: int) -> Response:
        scoping_tenant = Tenant.autodetect()
        matching_tenant = self._find_tenant(scoping_tenant, tenant)
        return (
            self.phonebook_service.get_phonebook(
                [matching_tenant['uuid']], PhonebookKey(id=phonebook_id)
            ),
            200,
        )

    @deprecated_endpoint
    @required_acl('dird.tenants.{tenant}.phonebooks.{phonebook_id}.update')
    @_default_error_route
    def put(self, tenant: str, phonebook_id: int) -> Response:
        scoping_tenant = Tenant.autodetect()
        matching_tenant = self._find_tenant(scoping_tenant, tenant)
        return (
            self.phonebook_service.edit_phonebook(
                [matching_tenant['uuid']],
                PhonebookKey(id=phonebook_id),
                get_json_body(),
            ),
            200,
        )
