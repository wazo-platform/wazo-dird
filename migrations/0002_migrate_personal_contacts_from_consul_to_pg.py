#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2016-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from consul import Consul
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from xivo.config_helper import read_config_file_hierarchy
from xivo_dird import database

DEFAULT_CONFIG = {
    'config_file': '/etc/xivo-dird/config.yml',
    'extra_config_files': '/etc/xivo-dird/conf.d',
}
PRIVATE_KEY = 'xivo/private'
PERSONAL_CONTACTS_KEY = 'xivo/private/{user_uuid}/contacts/personal/'
PERSONAL_CONTACT_KEY = 'xivo/private/{user_uuid}/contacts/personal/{contact_uuid}/'


def tree_from_consul(prefix, consul_entries):
    prefix = prefix or ''
    prefix_length = len(prefix)
    result = {}
    if consul_entries is None:
        return result
    for consul_entry in consul_entries:
        full_key = consul_entry['Key']
        if full_key.startswith(prefix):
            key_parts = full_key[prefix_length:].strip('/').split('/')
            parts_count = len(key_parts)
            value = (consul_entry.get('Value') or '').decode('utf-8')
            tree = result
            for part_index, key_part in enumerate(key_parts):
                default = {} if part_index < parts_count - 1 else value
                tree = tree.setdefault(key_part, default)
    return result


def list_personal_contacts(personal_data, uuid):
    for contact_id, contact in personal_data.get(uuid, {}).get('contacts', {}).get('personal', {}).iteritems():
        key = PERSONAL_CONTACT_KEY.format(user_uuid=uuid, contact_uuid=contact_id)
        yield key, contact


def list_users_uuid(personal_data):
    uuids = set()
    for uuid in personal_data.iterkeys():
        if uuid in uuids:
            continue
        uuids.add(uuid)
        yield uuid


def main():
    dird_config = read_config_file_hierarchy(DEFAULT_CONFIG)
    client = Consul(**dird_config['consul'])
    _, raw_private = client.kv.get(PRIVATE_KEY, recurse=True)
    personal_data = tree_from_consul(PRIVATE_KEY, raw_private)
    Session = scoped_session(sessionmaker())
    engine = create_engine(dird_config['db_uri'])
    Session.configure(bind=engine)
    crud = database.PersonalContactCRUD(Session)

    for uuid in list_users_uuid(personal_data):
        contacts = [c for (__, c) in list_personal_contacts(personal_data, uuid) if 'id' in c]
        crud.create_personal_contacts(uuid, contacts)

    client.kv.delete(PERSONAL_CONTACTS_KEY, recurse=True)


if __name__ == '__main__':
    main()
