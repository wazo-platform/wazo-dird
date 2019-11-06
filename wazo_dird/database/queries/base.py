# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import hashlib
import json

from contextlib import contextmanager
from sqlalchemy import exc
from wazo_dird.exception import DatabaseServiceUnavailable
from wazo_dird.database import Tenant, User

from .. import ContactFields


def delete_user(session, user_uuid):
    session.query(User).filter(User.user_uuid == user_uuid).delete()


def extract_constraint_name(error):
    try:
        return error.orig.diag.constraint_name
    except AttributeError:
        return None


def list_contacts_by_uuid(session, uuids):
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
    return list(result.values())


def compute_contact_hash(contact_info):
    d = dict(contact_info)
    d.pop('id', None)
    string_representation = json.dumps(d, sort_keys=True).encode('utf-8')
    return hashlib.sha1(string_representation).hexdigest()


class BaseDAO:
    def __init__(self, Session):
        self._Session = Session

    def flush_or_raise(self, session, Exception_, *args, **kwargs):
        try:
            session.flush()
        except exc.IntegrityError:
            session.rollback()
            raise Exception_(*args, **kwargs)

    @contextmanager
    def new_session(self):
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

    def _create_tenant(self, s, uuid):
        s.add(Tenant(uuid=uuid))
        try:
            s.flush()
        except exc.IntegrityError:
            s.rollback()

    def _get_dird_user(self, session, user_uuid):
        user = session.query(User).filter(User.user_uuid == user_uuid).first()
        if not user:
            user = User(user_uuid=user_uuid)
            session.add(user)
            session.flush()

        return user
