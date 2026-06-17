# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import csv
import logging
from typing import TYPE_CHECKING, Any, cast

from wazo_dird import BaseServicePlugin, database, exception
from wazo_dird.database.helpers import Session

if TYPE_CHECKING:
    from wazo_dird.config import Config
    from wazo_dird.controller import Controller
    from wazo_dird.database.queries.base import ContactInfo
    from wazo_dird.plugin_manager import ServiceDependencies
    from wazo_dird.plugins.personal_backend.plugin import PersonalBackend
    from wazo_dird.source_manager import SourceManager

logger = logging.getLogger(__name__)


UNIQUE_COLUMN = 'id'


class PersonalImportError(ValueError):
    pass


class PersonalServicePlugin(BaseServicePlugin):
    def load(self, dependencies: ServiceDependencies) -> _PersonalService:
        try:
            config = dependencies['config']
            source_manager = dependencies['source_manager']
            controller = dependencies['controller']
        except KeyError:
            msg = (
                '%s should be loaded with "config" and "source_manager" but received: %s'
                % (self.__class__.__name__, ','.join(dependencies.keys()))
            )
            raise ValueError(msg)

        crud = database.PersonalContactCRUD(Session)
        return _PersonalService(config, source_manager, crud, controller)


class _PersonalService:
    NoSuchContact = exception.NoSuchContact
    DuplicatedContactException = exception.DuplicatedContactException

    class InvalidPersonalContact(ValueError):
        def __init__(self, errors: list[str]) -> None:
            message = f"Invalid personal contact: {errors}"
            ValueError.__init__(self, message)
            self.errors = errors

    def __init__(
        self,
        config: Config,
        source_manager: SourceManager,
        crud: database.PersonalContactCRUD,
        controller: Controller,
    ) -> None:
        self._crud = crud
        self._config = config
        self._source_manager = source_manager
        self._controller = controller

    def create_contact(
        self, contact_infos: dict[str, Any], user_uuid: str, tenant_uuid: str
    ) -> dict[str, Any] | None:
        self.validate_contact(contact_infos)
        return self._crud.create_personal_contact(tenant_uuid, user_uuid, contact_infos)

    def create_contacts(
        self, contact_infos: csv.DictReader[str], user_uuid: str, tenant_uuid: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        errors: list[dict[str, Any]] = []
        to_add: list[dict[str, Any]] = []
        existing_contact_uuids = {
            contact['id'] for contact in self._crud.list_personal_contacts()
        }

        for contact_info in contact_infos:
            try:
                if None in contact_info.keys():
                    raise PersonalImportError('too many fields')
                if None in contact_info.values():
                    raise PersonalImportError('missing fields')

                self.validate_contact(contact_info, existing_contact_uuids)
                to_add.append(contact_info)
            except self.InvalidPersonalContact as e:
                errors.append({'errors': e.errors, 'line': contact_infos.line_num})
            except PersonalImportError as e:
                errors.append({'errors': [str(e)], 'line': contact_infos.line_num})

        return (
            self._crud.create_personal_contacts(tenant_uuid, user_uuid, to_add),
            errors,
        )

    def get_contact(self, contact_id: str, user_uuid: str) -> ContactInfo:
        return self._crud.get_personal_contact(user_uuid, contact_id)

    def edit_contact(
        self,
        contact_id: str,
        contact_infos: dict[str, Any],
        user_uuid: str,
        tenant_uuid: str,
    ) -> dict[str, Any] | None:
        self.validate_contact(contact_infos)
        return self._crud.edit_personal_contact(
            tenant_uuid, user_uuid, contact_id, contact_infos
        )

    def remove_contact(self, contact_id: str, user_uuid: str) -> None:
        self._crud.delete_personal_contact(user_uuid, contact_id)

    def purge_contacts(self, user_uuid: str) -> None:
        self._crud.delete_all_personal_contacts(user_uuid)

    def list_contacts(self, tenant_uuid: str, user_uuid: str) -> list[Any]:
        personal_source = self._find_personal_source(tenant_uuid)
        if not personal_source:
            logger.info('no personal source configured for tenant %s', tenant_uuid)
            return []

        contacts = self._crud.list_personal_contacts(user_uuid)
        source = cast(
            'PersonalBackend', self._source_manager.get(personal_source['uuid'])
        )
        formatted_contacts = source.format_contacts(cast('list[ContactInfo]', contacts))
        return formatted_contacts

    def list_contacts_raw(
        self, user_uuid: str, search_params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        return self._crud.list_personal_contacts(user_uuid, search_params=search_params)

    def _find_personal_source(self, tenant_uuid: str) -> Any:
        source_service = self._controller.services['source']
        for source in source_service.list_('personal', [tenant_uuid]):
            return source

    @staticmethod
    def validate_contact(
        contact_infos: dict[str, Any], existing_contact_uuids: set[str] | None = None
    ) -> None:
        errors: list[str] = []

        if any(not hasattr(key, 'encode') for key in contact_infos):
            errors.append('all keys must be strings')

        if any(not hasattr(value, 'encode') for value in contact_infos.values()):
            errors.append('all values must be strings')

        if '' in contact_infos:
            errors.append('"" is a forbidden in keys')

        if errors:
            raise _PersonalService.InvalidPersonalContact(errors)

        if existing_contact_uuids:
            uuid = contact_infos.get('id', contact_infos.get('uuid'))
            if uuid and uuid in existing_contact_uuids:
                raise PersonalImportError(f'contact "{uuid}" already exist')


class DisabledPersonalSource:
    def list(self, *args: Any, **kwargs: Any) -> list[Any]:
        return []
