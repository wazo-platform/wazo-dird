#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2016-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from consul import Consul
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from xivo.config_helper import read_config_file_hierarchy

from xivo_dird import database, exception


DEFAULT_CONFIG = {
    'config_file': '/etc/xivo-dird/config.yml',
    'extra_config_files': '/etc/xivo-dird/conf.d',
}
PRIVATE_KEY = 'xivo/private'


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


def get_all_favorites(client):
    _, raw_private = client.kv.get(PRIVATE_KEY, recurse=True)
    personal_data = tree_from_consul(PRIVATE_KEY, raw_private)
    for xivo_user_uuid, storage in personal_data.iteritems():
        for source, id_dict in storage.get('contacts', {}).get('favorites', {}).iteritems():
            for id_ in id_dict:
                yield (xivo_user_uuid, source, id_)


def main():
    dird_config = read_config_file_hierarchy(DEFAULT_CONFIG)
    client = Consul(**dird_config['consul'])
    Session = scoped_session(sessionmaker())
    engine = create_engine(dird_config['db_uri'])
    Session.configure(bind=engine)
    crud = database.FavoriteCRUD(Session)

    for xivo_user_uuid, source, id_ in get_all_favorites(client):
        try:
            crud.create(xivo_user_uuid, source, id_)
        except exception.DuplicatedFavoriteException:
            pass

    client.kv.delete(PRIVATE_KEY, recurse=True)


if __name__ == '__main__':
    main()
