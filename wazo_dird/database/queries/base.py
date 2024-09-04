# Copyright 2019-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from itertools import islice
from typing import Literal, TypedDict, cast

from sqlalchemy import exc
from sqlalchemy.orm import Session as BaseSession
from sqlalchemy.orm import scoped_session

from wazo_dird.database import Tenant, User
from wazo_dird.exception import DatabaseServiceUnavailable

from .. import ContactFields


def delete_user(session: BaseSession, user_uuid: str):
    session.query(User).filter(User.user_uuid == user_uuid).delete()


def extract_constraint_name(error: exc.DBAPIError):
    try:
        return error.orig.diag.constraint_name
    except AttributeError:
        return None


class ContactInfo(TypedDict, total=False):
    id: str


def list_contacts_by_uuid(session: BaseSession, uuids: list[str]) -> list[ContactInfo]:
    if not uuids:
        return []

    contact_fields = session.query(ContactFields).filter(
        ContactFields.contact_uuid.in_(uuids)
    )
    result = {}
    for contact_field in contact_fields.all():
        uuid = contact_field.contact_uuid
        if uuid not in result:
            result[uuid] = {'id': uuid}
        result[uuid][contact_field.name] = contact_field.value
    return cast(list[ContactInfo], list(result.values()))


def compute_contact_hash(contact_info: Mapping) -> str:
    d = dict(contact_info)
    d.pop('id', None)
    string_representation = json.dumps(d, sort_keys=True).encode('utf-8')
    return hashlib.sha1(string_representation).hexdigest()


Direction = Literal['asc', 'desc']


class Parameters(TypedDict):
    direction: Direction
    order: str | None
    limit: int | None
    offset: int
    search: str | None


class BaseDAO:
    SORT_DIRECTIONS: dict[Direction, None] = {
        'asc': None,
        'desc': None,
    }

    DEFAULTS: Parameters = {
        'search': None,
        'order': None,
        'direction': 'asc',
        'limit': None,
        'offset': 0,
    }

    def __init__(self, Session: scoped_session):
        self._Session = Session

    def flush_or_raise(
        self, session: BaseSession, Exception_: type[Exception], *args, **kwargs
    ):
        try:
            session.flush()
        except exc.IntegrityError:
            session.rollback()
            raise Exception_(*args, **kwargs)

    @contextmanager
    def new_session(self) -> Iterator[BaseSession]:
        session = self._Session()
        try:
            yield session
            session.commit()
        except exc.OperationalError:
            session.rollback()
            raise DatabaseServiceUnavailable()
        except Exception:
            session.rollback()
            raise
        finally:
            self._Session.remove()

    def _create_tenant(self, s: BaseSession, uuid: str):
        s.add(Tenant(uuid=uuid))
        try:
            s.flush()
        except exc.IntegrityError:
            s.rollback()

    def _get_dird_user(self, session: BaseSession, user_uuid: str):
        user = session.query(User).filter(User.user_uuid == user_uuid).first()
        if not user:
            user = User(user_uuid=user_uuid)
            session.add(user)
            session.flush()

        return user

    def _generate_parameters(self, parameters: dict | None) -> Parameters:
        new_params = dict(self.DEFAULTS)
        if parameters:
            new_params.update(parameters)
        return cast(Parameters, new_params)

    def _apply_search_params(
        self,
        rows,
        order: str | None,
        limit: int | None,
        offset: int,
        reverse: bool,
    ):
        if order:
            try:
                rows = sorted(
                    rows,
                    key=lambda x: unicodedata.normalize('NFKD', x[order]),
                    reverse=reverse,
                )
            except KeyError:
                raise ValueError(f"order: column '{order}' was not found")
        elif reverse:
            rows = reversed(rows)

        return list(islice(rows, offset, offset + limit if limit else None))

    def validate_parameters(self, parameters: Parameters):
        if int(parameters['offset']) < 0:
            raise ValueError('offset must be positive number')

        if parameters['limit'] is not None and int(parameters['limit']) <= 0:
            raise ValueError('limit must be a positive number')

        if parameters['direction'] not in self.SORT_DIRECTIONS.keys():
            raise ValueError('direction must be asc or desc')

    def _extract_search_params(
        self, parameters: dict | None
    ) -> tuple[str | None, int | None, int, bool]:
        _parameters = self._generate_parameters(parameters)
        self.validate_parameters(_parameters)

        order = _parameters.get('order', None)
        limit = _parameters.get('limit', None)
        if limit is not None:
            limit = int(limit)
        offset = int(_parameters.get('offset', 0))
        reverse = not (_parameters.get('direction', 'asc') == 'asc')
        return order, limit, offset, reverse
