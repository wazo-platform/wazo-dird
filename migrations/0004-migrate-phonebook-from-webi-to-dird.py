#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2016-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from __future__ import print_function

import os
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from xivo.config_helper import read_config_file_hierarchy

from xivo_dird import database, exception


DEFAULT_CONFIG = {
    'config_file': '/etc/xivo-dird/config.yml',
    'extra_config_files': '/etc/xivo-dird/conf.d',
}

DATA_FILENAME = '/var/lib/xivo-upgrade/phonebook_dump.json'
DEFAULT_PHONEBOOK = 'xivo'


def _get_or_create_phonebook(crud, entity, name):
    try:
        return crud.create(entity, {'name': name})['id']
    except exception.DuplicatedPhonebookException:
        for phonebook in crud.list(entity, search=name):
            if phonebook['name'] == name:
                return phonebook['id']

    msg = "Failed to create of find phonebook {} for tenant {}".format(name, entity)
    raise RuntimeError(msg)


def _get_session():
    dird_config = read_config_file_hierarchy(DEFAULT_CONFIG)
    Session = scoped_session(sessionmaker())
    engine = create_engine(dird_config['db_uri'])
    Session.configure(bind=engine)
    return Session


def main():
    if not os.path.exists(DATA_FILENAME):
        return

    Session = _get_session()

    phonebook_crud = database.PhonebookCRUD(Session)
    contact_crud = database.PhonebookContactCRUD(Session)

    with open(DATA_FILENAME, 'r') as f:
        entities, contacts = json.load(f)

    for entity in entities:
        print('creating default phonebook for tenant {}'.format(entity), end='... ')
        phonebook_id = _get_or_create_phonebook(phonebook_crud, entity, DEFAULT_PHONEBOOK)
        contact_crud.create_many(entity, phonebook_id, contacts)
        print('done')

    os.unlink(DATA_FILENAME)


if __name__ == '__main__':
    main()
