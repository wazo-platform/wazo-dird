# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Avencall
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

import itertools
import logging

from consul import Consul

from contextlib import contextmanager
from xivo_dird import BaseSourcePlugin
from xivo_dird import make_result_class

logger = logging.getLogger(__name__)

PERSONAL_CONTACTS_KEY = 'xivo/private/{user_uuid}/contacts/personal/'
PERSONAL_CONTACT_KEY = 'xivo/private/{user_uuid}/contacts/personal/{contact_uuid}/'
PERSONAL_CONTACT_ATTRIBUTE_KEY = 'xivo/private/{user_uuid}/contacts/personal/{contact_uuid}/{attribute}'
UNIQUE_COLUMN = 'id'


def match(term, actual):
    return term.lower() in actual.lower()


class PersonalBackend(BaseSourcePlugin):

    def load(self, config):
        logger.debug('Loading personal source')
        self._SourceResult = make_result_class(
            config['config']['name'],
            UNIQUE_COLUMN,
            config['config'].get(self.FORMAT_COLUMNS, {}),
            is_personal=True,
            is_deletable=True
        )
        self._searched_columns = config['config'].get(self.SEARCHED_COLUMNS, [])
        self._config = config['main_config']

    def search(self, term, args=None):
        logger.debug('Searching personal contacts with %s', term)
        contacts = []
        user_uuid = args['token_infos']['auth_id']
        consul_key = PERSONAL_CONTACTS_KEY.format(user_uuid=user_uuid)
        with self._consul(token=args['token_infos']['token']) as consul:
            _, contact_keys = consul.kv.get(consul_key, keys=True, separator='/')
            contact_keys = contact_keys or []
            contact_ids = [contact_key[len(consul_key):-1] for contact_key in contact_keys]
            for contact_id, attribute in itertools.product(contact_ids, self._searched_columns):
                consul_key = PERSONAL_CONTACT_ATTRIBUTE_KEY.format(user_uuid=user_uuid,
                                                                   contact_uuid=contact_id,
                                                                   attribute=attribute)
                _, result = consul.kv.get(consul_key)
                if not result:
                    continue
                if not result['Value']:
                    continue
                if match(term, result['Value'].decode('utf-8')):
                    contacts.append(contact_id)

        return self.list(contacts, args)

    def list(self, source_entry_ids, args):
        logger.debug('Listing personal contacts')
        user_uuid = args['token_infos']['auth_id']
        contact_keys = [PERSONAL_CONTACT_KEY.format(user_uuid=user_uuid,
                                                    contact_uuid=contact_uuid)
                        for contact_uuid in source_entry_ids]
        contacts = []
        with self._consul(token=args['token_infos']['token']) as consul:
            for contact_key in contact_keys:
                _, consul_dict = consul.kv.get(contact_key, recurse=True)
                if consul_dict:
                    contact = self._SourceResult(dict_from_consul(contact_key, consul_dict))
                    contacts.append(contact)
        return contacts

    @contextmanager
    def _consul(self, token):
        yield Consul(token=token, **self._config['consul'])


def dict_from_consul(prefix, consul_dict):
    result = {}
    if consul_dict is None:
        return result
    for consul_kv in consul_dict:
        if consul_kv['Key'].startswith(prefix):
            key = consul_kv['Key'][len(prefix):]
            value = consul_kv['Value']
            result[key] = value
    return result
