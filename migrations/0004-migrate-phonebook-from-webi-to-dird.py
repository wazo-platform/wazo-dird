#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

from __future__ import print_function

import os
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from xivo.config_helper import read_config_file_hierarchy

from xivo_dird.core import database, exception


DEFAULT_CONFIG = {
    'config_file': '/etc/xivo-dird/config.yml',
    'extra_config_files': '/etc/xivo-dird/conf.d',
}

DATA_FILENAME = '/var/lib/xivo-upgrade/phonebook_dump.json'
DEFAULT_PHONEBOOK = 'xivo'


def _get_or_create_phonebook(crud, entity, name):
    try:
        return crud.create(entity, {'name': DEFAULT_PHONEBOOK})['id']
    except exception.DuplicatedPhonebookException:
        for phonebook in crud.list(entity, search=DEFAULT_PHONEBOOK):
            if phonebook['name'] == DEFAULT_PHONEBOOK:
                return phonebook['id']

    msg = "Failed to create of find phonebook {} for tenant {}".format(DEFAULT_PHONEBOOK, entity)
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
