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

from contextlib import contextmanager
from unidecode import unidecode
from xivo_dird import BaseSourcePlugin
from xivo_dird import make_result_class
from xivo_dird.core.consul import PERSONAL_CONTACTS_KEY
from xivo_dird.core.consul import PERSONAL_CONTACT_KEY
from xivo_dird.core.consul import dict_from_consul
from xivo_dird.core.consul import new_consul
from xivo_dird.core.consul import tree_from_consul

logger = logging.getLogger(__name__)

UNIQUE_COLUMN = 'id'


def match(term, actual):
    return unidecode(term).lower() in unidecode(actual).lower()


def remove_empty_values(dict_):
    return {attribute: value for attribute, value in dict_.iteritems() if value}


class PersonalBackend(BaseSourcePlugin):

    def load(self, config):
        logger.debug('Loading personal source')
        result_class = make_result_class(
            config['config']['name'],
            UNIQUE_COLUMN,
            config['config'].get(self.FORMAT_COLUMNS, {}),
            is_personal=True,
            is_deletable=True
        )
        self._SourceResult = lambda contact: result_class(remove_empty_values(contact))
        self._searched_columns = config['config'].get(self.SEARCHED_COLUMNS, [])
        self._first_matched_columns = config['config'].get(self.FIRST_MATCHED_COLUMNS, [])
        self._config = config['main_config']

    def search(self, term, args=None):
        logger.debug('Searching personal contacts with %s', term)
        matching_contact_ids = set()
        token = args['token']
        user_uuid = args['auth_id']
        contacts_tree = self._get_personal_contacts_tree(user_uuid, token)

        for contact_id, attribute in itertools.product(contacts_tree, self._searched_columns):
            attribute_value = contacts_tree[contact_id].get(attribute)
            if not attribute_value:
                continue
            if match(term, attribute_value):
                matching_contact_ids.add(contact_id)

        return [self._SourceResult(contacts_tree[contact_id]) for contact_id in matching_contact_ids]

    def first_match(self, term, args=None):
        logger.debug('First matching personal contacts with %s', term)
        user_uuid = args['auth_id']
        token = args['token']
        contacts_tree = self._get_personal_contacts_tree(user_uuid, token)

        for contact_id, attribute in itertools.product(contacts_tree, self._first_matched_columns):
            attribute_value = contacts_tree[contact_id].get(attribute)
            if term == attribute_value:
                return self._SourceResult(contacts_tree[contact_id])
        return None

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
                    contacts.append(self._SourceResult(dict_from_consul(contact_key, consul_dict)))
        return contacts

    def _get_personal_contacts_tree(self, user_uuid, token):
        consul_key = PERSONAL_CONTACTS_KEY.format(user_uuid=user_uuid)
        with self._consul(token=token) as consul:
            _, contacts = consul.kv.get(consul_key, recurse=True)
        return tree_from_consul(consul_key, contacts)

    @contextmanager
    def _consul(self, token):
        yield new_consul(self._config, token=token)
