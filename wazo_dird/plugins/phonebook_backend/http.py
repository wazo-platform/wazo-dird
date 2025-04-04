# Copyright 2019-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from typing import cast

from flask import Request, request

from wazo_dird.auth import required_acl
from wazo_dird.config import AuthConfig
from wazo_dird.database.queries.phonebook import PhonebookCRUD, PhonebookKey
from wazo_dird.exception import (
    InvalidConfigError,
    InvalidSourceConfigError,
    NoSuchPhonebook,
    NoSuchPhonebookAPIException,
)
from wazo_dird.helpers import SourceConfig, SourceItem, SourceList
from wazo_dird.http import AuthResource
from wazo_dird.plugin_helpers.tenant import get_tenant_uuids
from wazo_dird.plugins.phonebook_service.plugin import _PhonebookService
from wazo_dird.plugins.source_service.plugin import _SourceService
from wazo_dird.utils import projection

from .schemas import contact_list_schema, list_schema, source_list_schema, source_schema

request: Request  # type: ignore[no-redef]


logger = logging.getLogger(__name__)


def get_count_params(args: dict) -> dict:
    return projection(args, ['search'])


class PhonebookSourceInfo(SourceConfig):
    phonebook_uuid: str
    phonebook_name: str
    phonebook_description: str


class PhonebookList(SourceList):
    list_schema = list_schema
    source_schema = source_schema
    source_list_schema = source_list_schema

    def __init__(
        self,
        backend: str,
        service: _SourceService,
        auth_config: AuthConfig,
        phonebook_dao: PhonebookCRUD,
    ):
        super().__init__(backend, service, auth_config)
        self.phonebook_dao = phonebook_dao

    @required_acl('dird.backends.phonebook.sources.read')
    def get(self):
        return super().get()

    def _create_new_source(self, source_data: dict, tenant_uuid: str) -> dict:
        try:
            return super()._create_new_source(source_data, tenant_uuid)
        except NoSuchPhonebook as ex:
            raise NoSuchPhonebookAPIException(
                resource='/backends/phonebook/sources',
                visible_tenants=[tenant_uuid],
                phonebook_key=PhonebookKey(uuid=source_data['phonebook_uuid']),
            ) from ex

    @required_acl('dird.backends.phonebook.sources.create')
    def post(self):
        return super().post()


class PhonebookItem(SourceItem):
    source_schema = source_schema

    def __init__(
        self,
        backend: str,
        service: _SourceService,
        auth_config: AuthConfig,
        phonebook_dao: PhonebookCRUD,
    ):
        super().__init__(backend, service, auth_config)
        self.phonebook_dao = phonebook_dao

    @required_acl('dird.backends.phonebook.sources.{source_uuid}.delete')
    def delete(self, source_uuid):
        return super().delete(source_uuid)

    @required_acl('dird.backends.phonebook.sources.{source_uuid}.read')
    def get(self, source_uuid):
        return super().get(source_uuid)

    def _edit_source(
        self, source_uuid: str, visible_tenants: list[str], source_data: dict
    ):
        try:
            return super()._edit_source(source_uuid, visible_tenants, source_data)
        except InvalidSourceConfigError as ex:
            if 'pgerror' in ex.details and 'phonebook_uuid' in ex.details['pgerror']:
                raise NoSuchPhonebookAPIException(
                    resource='/backends/phonebook/sources',
                    visible_tenants=visible_tenants,
                    phonebook_key=PhonebookKey(uuid=source_data['phonebook_uuid']),
                )
            raise

    @required_acl('dird.backends.phonebook.sources.{source_uuid}.update')
    def put(self, source_uuid):
        return super().put(source_uuid)


class PhonebookContactList(AuthResource):
    BACKEND = 'phonebook'
    _phonebook_service: _PhonebookService
    _source_service: _SourceService

    def __init__(
        self, source_service: _SourceService, phonebook_service: _PhonebookService
    ):
        self._source_service = source_service
        self._phonebook_service = phonebook_service

    @required_acl('dird.backends.phonebook.sources.{source_uuid}.contacts.read')
    def get(self, source_uuid):
        visible_tenants = get_tenant_uuids(recurse=False)
        list_params = contact_list_schema.load(request.args)
        count_params = get_count_params(list_params)
        source_config = cast(
            PhonebookSourceInfo,
            self._source_service.get(self.BACKEND, str(source_uuid), visible_tenants),
        )
        logger.debug("Found source (uuid=%s): %s", source_uuid, str(source_config))

        try:
            phonebook_key = PhonebookKey(uuid=source_config['phonebook_uuid'])
        except KeyError:
            logger.error(
                'Source %s missing required phonebook_uuid. '
                'Sources without a phonebook_uuid cannot be queried through this API.'
            )
            raise InvalidConfigError(
                f'/backends/phonebook/{source_uuid}/contacts',
                'phonebook source missing phonebook_uuid',
            )

        try:
            total_count = self._phonebook_service.count_contact(
                visible_tenants, phonebook_key
            )
            logger.debug(
                "total count of contacts for phonebook (%s) and visible tenants %s: %d",
                str(phonebook_key),
                str(visible_tenants),
                total_count,
            )
            filtered_count = self._phonebook_service.count_contact(
                visible_tenants, phonebook_key, **count_params
            )
            logger.debug(
                "filtered count of contacts for phonebook (%s) "
                "and visible tenants %s with search params(%s): %d",
                str(phonebook_key),
                str(visible_tenants),
                str(count_params),
                filtered_count,
            )
            contacts = self._phonebook_service.list_contacts(
                visible_tenants=visible_tenants,
                phonebook_key=phonebook_key,
                **list_params,
            )
            logger.debug(
                "Retrieved %d contacts for phonebook (%s) "
                "and visible tenants %s with search params(%s)",
                len(contacts),
                str(phonebook_key),
                str(visible_tenants),
                str(list_params),
            )
        except NoSuchPhonebook as ex:
            raise NoSuchPhonebookAPIException(
                resource='phonebook-source-contacts',
                visible_tenants=visible_tenants,
                phonebook_key=dict(phonebook_key),
            ) from ex

        return (
            {'filtered': filtered_count, 'items': contacts, 'total': total_count},
            200,
        )
