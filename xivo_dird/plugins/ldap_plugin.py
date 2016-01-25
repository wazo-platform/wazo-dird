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

import itertools
import ldap
import logging
import re
import threading
import uuid

from ldap.filter import escape_filter_chars
from xivo_dird import BaseSourcePlugin
from xivo_dird import make_result_class

logger = logging.getLogger(__name__)


class LDAPPlugin(BaseSourcePlugin):

    def __init__(self, *args, **kwargs):
        super(LDAPPlugin, self).__init__(*args, **kwargs)
        self.ldap_factory = _LDAPFactory()
        self._lock = threading.Lock()

    def load(self, args):
        self._ldap_config = self.ldap_factory.new_ldap_config(args['config'])
        self._ldap_result_formatter = self.ldap_factory.new_ldap_result_formatter(self._ldap_config)
        self._ldap_client = self.ldap_factory.new_ldap_client(self._ldap_config)
        self._ldap_client.set_up()

    def unload(self):
        self._ldap_client.close()

    def search(self, term, args=None):
        filter_str = self._ldap_config.build_search_filter(term)

        return self._search_and_format(filter_str)

    def first_match(self, term, args=None):
        filter_str = self._ldap_config.build_first_match_filter(term)

        return self._first_match_and_format(filter_str)

    def list(self, uids, args=None):
        # XXX what is the character encoding used in uids ?
        if not self._ldap_config.unique_column():
            return []
        if not uids:
            return []

        filter_str = self._ldap_config.build_list_filter(uids)

        return self._search_and_format(filter_str)

    def _search_and_format(self, filter_str):
        with self._lock:
            raw_results = self._ldap_client.search(filter_str)

        return self._ldap_result_formatter.format(raw_results)

    def _first_match_and_format(self, filter_str):
        with self._lock:
            raw_results = self._ldap_client.search(filter_str, 1)

        if not raw_results:
            return None

        dn, attrs = raw_results[0]
        if not dn:
            return None
        return self._ldap_result_formatter.format_one_result(attrs)


class _LDAPFactory(object):

    def new_ldap_config(self, config):
        return _LDAPConfig(config)

    def new_ldap_client(self, ldap_config):
        return _LDAPClient(ldap_config)

    def new_ldap_result_formatter(self, ldap_config):
        return _LDAPResultFormatter(ldap_config)


class _LDAPConfig(object):

    DEFAULT_LDAP_USERNAME = ''
    DEFAULT_LDAP_PASSWORD = ''
    DEFAULT_LDAP_NETWORK_TIMEOUT = 0.3
    DEFAULT_LDAP_TIMEOUT = 1.0

    def __init__(self, config):
        if not config.get('ldap_custom_filter') and not config.get(BaseSourcePlugin.SEARCHED_COLUMNS):
            raise LookupError("%s need a searched_columns OR"
                              "ldap_custom_filter in it's configuration" % config.get('name'))

        self._config = config

    def has_binary_uuid(self):
        return self._config.get('unique_column_format', 'string') == 'binary_uuid'

    def name(self):
        return self._config['name']

    def unique_column(self):
        return self._config.get(BaseSourcePlugin.UNIQUE_COLUMN)

    def format_columns(self):
        return self._config.get(BaseSourcePlugin.FORMAT_COLUMNS)

    def first_matched_columns(self):
        return self._config.get(BaseSourcePlugin.FIRST_MATCHED_COLUMNS, [])

    def searched_columns(self):
        return self._config.get(BaseSourcePlugin.SEARCHED_COLUMNS, [])

    def ldap_uri(self):
        return self._config['ldap_uri']

    def ldap_base_dn(self):
        return self._config['ldap_base_dn']

    def ldap_username(self):
        return self._config.get('ldap_username', self.DEFAULT_LDAP_USERNAME)

    def ldap_password(self):
        return self._config.get('ldap_password', self.DEFAULT_LDAP_PASSWORD)

    def ldap_network_timeout(self):
        return self._config.get('ldap_network_timeout', self.DEFAULT_LDAP_NETWORK_TIMEOUT)

    def ldap_timeout(self):
        return self._config.get('ldap_timeout', self.DEFAULT_LDAP_TIMEOUT)

    def attributes(self):
        format_columns = self._config.get(BaseSourcePlugin.FORMAT_COLUMNS)
        if not format_columns:
            return None

        attributes = []
        for column in format_columns.itervalues():
            fields = re.findall(r'{(\w+)}', column)
            attributes.extend(fields)
        unique_column = self._config.get(BaseSourcePlugin.UNIQUE_COLUMN)
        if unique_column and unique_column not in attributes:
            attributes.append(unique_column)

        return attributes

    def build_search_filter(self, term):
        term_escaped = escape_filter_chars(term)
        ldap_custom_filter = self._config.get('ldap_custom_filter')
        searched_columns = self.searched_columns()

        if ldap_custom_filter and searched_columns:
            custom_filter = self._build_search_filter_from_custom_filter(term_escaped)
            generated_filter = self._build_search_filter_from_searched_columns(term_escaped)
            return self._build_filter_from_custom_and_generated_filter(custom_filter, generated_filter)
        elif ldap_custom_filter:
            return self._build_search_filter_from_custom_filter(term_escaped)
        elif searched_columns:
            return self._build_search_filter_from_searched_columns(term_escaped)
        return None

    def build_first_match_filter(self, term):
        term_escaped = escape_filter_chars(term)
        ldap_custom_filter = self._config.get('ldap_custom_filter')
        first_matched_columns = self.first_matched_columns()

        if ldap_custom_filter and first_matched_columns:
            custom_filter = self._build_search_filter_from_custom_filter(term_escaped)
            generated_filter = self._build_exact_search_filter_from_first_matched_columns(term_escaped)
            return self._build_filter_from_custom_and_generated_filter(custom_filter, generated_filter)
        elif ldap_custom_filter:
            return self._build_search_filter_from_custom_filter(term_escaped)
        elif first_matched_columns:
            return self._build_exact_search_filter_from_first_matched_columns(term_escaped)
        return None

    def _build_filter_from_custom_and_generated_filter(self, custom_filter, generated_filter):
        return u'(&{custom}{generated})'.format(custom=custom_filter, generated=generated_filter)

    def _build_search_filter_from_custom_filter(self, term_escaped):
        return self._config['ldap_custom_filter'].replace('%Q', term_escaped)

    def _build_search_filter_from_searched_columns(self, term_escaped):
        l = list('(%s=*%s*)' % (attr, term_escaped) for attr in self.searched_columns())
        return self._build_filter_from_list(l)

    def _build_exact_search_filter_from_first_matched_columns(self, term_escaped):
        l = list('(%s=%s)' % (attr, term_escaped) for attr in self.first_matched_columns())
        return self._build_filter_from_list(l)

    def _build_filter_from_list(self, l):
        if len(l) == 1:
            return l[0]
        else:
            return '(|%s)' % ''.join(l)

    def build_list_filter(self, uids):
        if not uids:
            return None

        unique_column = self._config[BaseSourcePlugin.UNIQUE_COLUMN]

        l = []
        for uid in self._convert_uids(uids):
            l.append('(%s=%s)' % (unique_column, uid))
        return self._build_filter_from_list(l)

    def _convert_uids(self, uids):
        if self.has_binary_uuid():
            return [self._convert_binary_uid(uid) for uid in uids]
        return uids

    def _convert_binary_uid(self, uid):
        uid = uuid.UUID(uid).hex
        return ''.join(character for byte in zip(itertools.repeat('\\'), uid[::2], uid[1::2]) for character in byte)


class _LDAPClient(object):

    def __init__(self, ldap_config, ldap_obj_factory=ldap.initialize):
        self._ldap_config = ldap_config
        self._ldap_obj_factory = ldap_obj_factory
        self._ldap_obj = None
        self._name = self._ldap_config.name()
        self._base_dn = self._ldap_config.ldap_base_dn()
        self._attributes = self._ldap_config.attributes()

    def close(self):
        if self._is_set_up():
            self._tear_down()

    def set_up(self):
        # This is an optional method. The main interest is that it will raise an exception
        # if the ldap_obj can't be initialized properly. This can be useful if you want to
        # fail early.
        if not self._is_set_up():
            self._set_up()

    def _is_set_up(self):
        return self._ldap_obj is not None

    def _set_up(self):
        self._ldap_obj = self._new_ldap_obj()
        self._bind()

    def _new_ldap_obj(self):
        ldap_obj = self._ldap_obj_factory(self._ldap_config.ldap_uri())
        ldap_obj.set_option(ldap.OPT_REFERRALS, 0)
        ldap_obj.set_option(ldap.OPT_NETWORK_TIMEOUT, self._ldap_config.ldap_network_timeout())
        ldap_obj.set_option(ldap.OPT_TIMEOUT, self._ldap_config.ldap_timeout())
        return ldap_obj

    def _bind(self):
        try:
            self._ldap_obj.simple_bind_s(self._ldap_config.ldap_username(), self._ldap_config.ldap_password())
        except ldap.LDAPError as e:
            logger.error('LDAP "%s": bind error: %r', self._name, e)
            self._tear_down()

    def _tear_down(self):
        self._ldap_obj.unbind_s()
        self._ldap_obj = None

    def search(self, filter_str, limit=-1):
        if self._is_set_up():
            retry = True
        else:
            self._set_up()
            if not self._is_set_up():
                return []
            retry = False

        results = self._search(filter_str, limit)
        if not self._is_set_up() and retry:
            self._set_up()
            if not self._is_set_up():
                return []
            results = self._search(filter_str, limit)

        return results

    def _search(self, filter_str, limit):
        results = []

        encoded_filter_str = filter_str.encode('utf-8')
        encoded_base_dn = self._base_dn.encode('utf-8')

        try:
            results = self._ldap_obj.search_ext_s(encoded_base_dn,
                                                  ldap.SCOPE_SUBTREE,
                                                  encoded_filter_str,
                                                  self._attributes,
                                                  sizelimit=limit)
        except ldap.FILTER_ERROR:
            logger.warning('LDAP "%s": search error: invalid filter "%s"', self._name, filter_str)
        except ldap.NO_SUCH_OBJECT:
            logger.warning('LDAP "%s": search error: no such object "%s"', self._name, self._ldap_config.ldap_base_dn())
        except ldap.TIMEOUT:
            logger.warning('LDAP "%s": search error: timed out')
        except ldap.LDAPError as e:
            logger.error('LDAP "%s": search error: %r', self._name, e)
            self._tear_down()

        return results


class _LDAPResultFormatter(object):

    def __init__(self, ldap_config):
        self._unique_column = ldap_config.unique_column()
        self._bin_uuid = ldap_config.has_binary_uuid()
        self._SourceResult = make_result_class(ldap_config.name(),
                                               self._unique_column,
                                               ldap_config.format_columns())

    def format(self, raw_results):
        results = []
        for dn, attrs in raw_results:
            if not dn:
                continue
            results.append(self.format_one_result(attrs))

        return results

    def format_one_result(self, attrs):
        fields = {}
        for name, values in attrs.iteritems():
            value = values[0]
            if name == self._unique_column and self._bin_uuid:
                value = unicode(uuid.UUID(bytes=value))
            else:
                value = value.decode('utf-8')
            fields[name] = value
        return self._SourceResult(fields)
