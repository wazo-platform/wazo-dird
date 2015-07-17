# -*- coding: utf-8 -*-

# Copyright (C) 2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import logging
import uuid

from consul import Consul

from contextlib import contextmanager
from xivo_dird import BaseService
from xivo_dird import BaseServicePlugin

logger = logging.getLogger(__name__)

PRIVATE_CONTACTS_KEY = 'xivo/private/{user_uuid}/contacts/personal/'
PRIVATE_CONTACT_KEY = 'xivo/private/{user_uuid}/contacts/personal/{contact_uuid}/'
PRIVATE_CONTACT_ATTRIBUTE_KEY = 'xivo/private/{user_uuid}/contacts/personal/{contact_uuid}/{attribute}'


class PrivatesServicePlugin(BaseServicePlugin):

    def load(self, args):
        try:
            config = args['config']
        except KeyError:
            msg = ('%s should be loaded with "config" but received: %s'
                   % (self.__class__.__name__, ','.join(args.keys())))
            raise ValueError(msg)

        return _PrivatesService(config)


class _PrivatesService(BaseService):

    def __init__(self, config):
        self._config = config

    def __call__(self):
        pass

    def create_contact(self, contact_infos, token_infos):
        contact_infos['id'] = str(uuid.uuid4())
        with self._consul(token=token_infos['token']) as consul:
            for attribute, value in contact_infos.iteritems():
                consul_key = PRIVATE_CONTACT_ATTRIBUTE_KEY.format(user_uuid=token_infos['auth_id'],
                                                                  contact_uuid=contact_infos['id'],
                                                                  attribute=attribute)
                consul.kv.put(consul_key, value)
        return contact_infos

    def remove_contact(self, contact_id, token_infos):
        with self._consul(token=token_infos['token']) as consul:
            consul_key = PRIVATE_CONTACT_KEY.format(user_uuid=token_infos['auth_id'],
                                                    contact_uuid=contact_id)
            consul.kv.delete(consul_key, recurse=True)

    def list_contacts(self, token_infos):
        user_uuid = token_infos['auth_id']
        consul_key = PRIVATE_CONTACTS_KEY.format(user_uuid=user_uuid)
        contacts = []
        with self._consul(token=token_infos['token']) as consul:
            _, contact_key_prefixes = consul.kv.get(consul_key, keys=True, separator='/')
            for key_prefix in contact_key_prefixes:
                _, consul_dict = consul.kv.get(key_prefix, recurse=True)
                contacts.append(dict_from_consul(key_prefix, consul_dict))
        return contacts

    @contextmanager
    def _consul(self, token):
        yield Consul(token=token, **self._config['consul'])


def dict_from_consul(prefix, consul_dict):
    return dict((consul_kv['Key'][len(prefix):], consul_kv['Value']) for consul_kv in consul_dict)