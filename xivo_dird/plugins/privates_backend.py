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

import logging

from consul import Consul

from contextlib import contextmanager
from xivo_dird import BaseSourcePlugin
from xivo_dird import make_result_class

logger = logging.getLogger(__name__)

PRIVATE_CONTACT_KEY = 'xivo/private/{user_uuid}/contacts/personal/{contact_uuid}/'


class PrivatesBackend(BaseSourcePlugin):

    def load(self, config):
        self._SourceResult = make_result_class(
            config['config']['name'],
            config['config'].get(self.UNIQUE_COLUMN),
            config['config'].get(self.FORMAT_COLUMNS, {}))
        self._config = config['main_config']

    def search(self, term, profile=None, args=None):
        return []

    def list(self, source_entry_ids, token_infos):
        user_uuid = token_infos['auth_id']
        contact_keys = [PRIVATE_CONTACT_KEY.format(user_uuid=user_uuid,
                                                   contact_uuid=contact_uuid)
                        for contact_uuid in source_entry_ids]
        contacts = []
        with self._consul(token=token_infos['token']) as consul:
            for contact_key in contact_keys:
                _, consul_dict = consul.kv.get(contact_key, recurse=True)
                contacts.append(self._SourceResult(dict_from_consul(contact_key, consul_dict)))
        return contacts

    @contextmanager
    def _consul(self, token):
        yield Consul(token=token, **self._config['consul'])


def dict_from_consul(prefix, consul_dict):
    result = {}
    for consul_kv in consul_dict:
        if consul_kv['Key'].startswith(prefix):
            key = consul_kv['Key'][len(prefix):]
            value = consul_kv['Value']
            result[key] = value
    return result
