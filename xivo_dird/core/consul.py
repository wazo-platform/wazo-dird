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
import urllib

PERSONAL_CONTACTS_KEY = 'xivo/private/{user_uuid}/contacts/personal/'
PERSONAL_CONTACT_KEY = 'xivo/private/{user_uuid}/contacts/personal/{contact_uuid}/'

logger = logging.getLogger(__name__)


def dict_from_consul(prefix, consul_dict):
    prefix_length = len(prefix)
    result = {}
    if consul_dict is None:
        return result
    for consul_kv in consul_dict:
        full_key = consul_kv['Key']
        if full_key.startswith(prefix):
            key = full_key[prefix_length:]
            value = (consul_kv.get('Value') or '').decode('utf-8')
            result[key] = value
    return result


def ls_from_consul(prefix, keys):
    keys = keys or []
    prefix_length = len(prefix)
    result = [key[prefix_length:].rstrip('/') for key in keys]
    return result


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


def dict_to_consul(prefix, dict_):
    prefix = prefix or ''
    dict_ = dict_ or {}
    result = {}
    for key, value in dict_.iteritems():
        full_key = urllib.quote('{}{}'.format(prefix, key))
        result[full_key] = value.encode('utf-8')
    return result
