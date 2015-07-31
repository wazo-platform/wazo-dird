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
from xivo_dird.core.consul import PERSONAL_CONTACTS_KEY
from xivo_dird.core.consul import PERSONAL_CONTACT_KEY
from xivo_dird.core.consul import PERSONAL_CONTACT_ATTRIBUTE_KEY
from xivo_dird.core.consul import dict_from_consul
from xivo_dird.core.consul import ls_from_consul

logger = logging.getLogger(__name__)


UNIQUE_COLUMN = 'id'


class _NoSuchPersonalContact(ValueError):
    def __init__(self, contact_id):
        message = "No such personal contact: {}".format(contact_id)
        super(_NoSuchPersonalContact, self).__init__(message)


class PersonalServicePlugin(BaseServicePlugin):

    def load(self, args):
        try:
            config = args['config']
            sources = args['sources']
        except KeyError:
            msg = ('%s should be loaded with "config" and "sources" but received: %s'
                   % (self.__class__.__name__, ','.join(args.keys())))
            raise ValueError(msg)

        return _PersonalService(config, sources)


class _PersonalService(BaseService):

    NoSuchPersonalContact = _NoSuchPersonalContact

    def __init__(self, config, sources):
        self._config = config
        self._source = next((source for source in sources.itervalues() if source.backend == 'personal'), DisabledPersonalSource())

    def __call__(self):
        pass

    def create_contact(self, contact_infos, token_infos):
        contact_infos[UNIQUE_COLUMN] = str(uuid.uuid4())
        with self._consul(token=token_infos['token']) as consul:
            for attribute, value in contact_infos.iteritems():
                consul_key = PERSONAL_CONTACT_ATTRIBUTE_KEY.format(user_uuid=token_infos['auth_id'],
                                                                   contact_uuid=contact_infos[UNIQUE_COLUMN],
                                                                   attribute=attribute)
                consul.kv.put(consul_key, value.encode('utf-8'))
        return contact_infos

    def get_contact(self, contact_id, token_infos):
        with self._consul(token=token_infos['token']) as consul:
            if not self._contact_exists(consul, token_infos['auth_id'], contact_id):
                raise _NoSuchPersonalContact(contact_id)
            consul_key = PERSONAL_CONTACT_KEY.format(user_uuid=token_infos['auth_id'],
                                                     contact_uuid=contact_id)
            _, consul_dict = consul.kv.get(consul_key, recurse=True)
        return dict_from_consul(consul_key, consul_dict)

    def edit_contact(self, contact_id, contact_infos, token_infos):
        with self._consul(token=token_infos['token']) as consul:
            if not self._contact_exists(consul, token_infos['auth_id'], contact_id):
                raise _NoSuchPersonalContact(contact_id)
            for attribute, value in contact_infos.iteritems():
                consul_key = PERSONAL_CONTACT_ATTRIBUTE_KEY.format(user_uuid=token_infos['auth_id'],
                                                                   contact_uuid=contact_id,
                                                                   attribute=attribute)
                consul.kv.put(consul_key, value.encode('utf-8'))
        return contact_infos

    def remove_contact(self, contact_id, token_infos):
        with self._consul(token=token_infos['token']) as consul:
            if not self._contact_exists(consul, token_infos['auth_id'], contact_id):
                raise _NoSuchPersonalContact(contact_id)
            consul_key = PERSONAL_CONTACT_KEY.format(user_uuid=token_infos['auth_id'],
                                                     contact_uuid=contact_id)
            consul.kv.delete(consul_key, recurse=True)

    def list_contacts(self, token_infos):
        user_uuid = token_infos['auth_id']
        consul_key = PERSONAL_CONTACTS_KEY.format(user_uuid=user_uuid)
        with self._consul(token_infos['token']) as consul:
            _, contact_keys = consul.kv.get(consul_key, keys=True, separator='/')
            contact_ids = ls_from_consul(consul_key, contact_keys)
            contacts = self._source.list(contact_ids, {'token_infos': token_infos})
        return contacts

    def list_contacts_raw(self, token_infos):
        user_uuid = token_infos['auth_id']
        consul_key = PERSONAL_CONTACTS_KEY.format(user_uuid=user_uuid)
        contacts = []
        with self._consul(token=token_infos['token']) as consul:
            _, contact_keys = consul.kv.get(consul_key, keys=True, separator='/')
            contact_keys = contact_keys or []
            for key_prefix in contact_keys:
                _, consul_dict = consul.kv.get(key_prefix, recurse=True)
                contacts.append(dict_from_consul(key_prefix, consul_dict))
        return contacts

    @contextmanager
    def _consul(self, token):
        yield Consul(token=token, **self._config['consul'])

    def _contact_exists(self, consul, user_uuid, contact_id):
        consul_key = PERSONAL_CONTACT_KEY.format(user_uuid=user_uuid,
                                                 contact_uuid=contact_id)
        _, result = consul.kv.get(consul_key, keys=True)
        return result is not None


class DisabledPersonalSource(object):
    def list(self, _source_entry_ids, _token_infos):
        return []
