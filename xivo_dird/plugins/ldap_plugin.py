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

import ldap
import logging
import threading

from ldap.filter import escape_filter_chars
from xivo_dird import BaseSourcePlugin
from xivo_dird import make_result_class

logger = logging.getLogger(__name__)


class LDAPPlugin(BaseSourcePlugin):

    def __init__(self, *args, **kwargs):
        super(LDAPPlugin, self).__init__(*args, **kwargs)
        self.ldap_factory = _LDAPFactory()
        self._ldap_client = None
        self._lock = threading.Lock()

    def load(self, args):
        self._ldap_config = self.ldap_factory.new_ldap_config(args['config'])
        self._ldap_result_formatter = self.ldap_factory.new_ldap_result_formatter(self._ldap_config)

        self._init_ldap_client()

    def unload(self):
        if self._ldap_client is None:
            return

        self._deinit_ldap_client()

    def search(self, term, profile, *args, **kwargs):
        term = term.encode('UTF-8')

        filter_str = self._ldap_config.build_search_filter(term)

        return self._search_and_format(filter_str)

    def list(self, uids):
        # XXX what is the character encoding used in uids ?
        if not self._ldap_config.unique_columns():
            return []

        filter_str = self._ldap_config.build_list_filter(uids)

        return self._search_and_format(filter_str)

    def _search_and_format(self, filter_str):
        # thread safe
        with self._lock:
            raw_results = self._search(filter_str)

        return self._ldap_result_formatter.format(raw_results)

    def _search(self, filter_str, retry=True):
        # not thread safe
        raw_results = []

        if self._ldap_client is None:
            if not self._init_ldap_client():
                return raw_results

        try:
            raw_results = self._ldap_client.search(filter_str)
        except ldap.FILTER_ERROR:
            logger.warning('LDAP source "%s": search error: invalid filter "%s"', self.name, filter_str)
        except ldap.NO_SUCH_OBJECT:
            logger.warning('LDAP source "%s": search error: no such object "%s"', self.name, self._ldap_config.ldap_base_dn())
        except ldap.TIMEOUT:
            logger.warning('LDAP source "%s": search error: timeout')
        except ldap.LDAPError as e:
            logger.error('LDAP source "%s": search error: %r', self.name, e)
            self._deinit_ldap_client()
            if retry and self._init_ldap_client():
                return self._search(filter_str, retry=False)

        return raw_results

    def _init_ldap_client(self):
        # not thread safe
        ldap_client = self.ldap_factory.new_ldap_client(self._ldap_config)
        try:
            ldap_client.bind()
        except ldap.LDAPError as e:
            logger.error('LDAP source "%s": bind error: %r', self.name, e)
            return False

        self._ldap_client = ldap_client
        return True

    def _deinit_ldap_client(self):
        # not thread safe
        self._ldap_client.unbind()
        self._ldap_client = None


class _LDAPFactory(object):

    def new_ldap_config(self, config):
        return _LDAPConfig(config)

    def new_ldap_client(self, ldap_config):
        return _LDAPClient(ldap_config, ldap.initialize(ldap_config.ldap_uri()))

    def new_ldap_result_formatter(self, ldap_config):
        return _LDAPResultFormatter(ldap_config)


class _LDAPConfig(object):

    DEFAULT_LDAP_USERNAME = ''
    DEFAULT_LDAP_PASSWORD = ''
    DEFAULT_LDAP_NETWORK_TIMEOUT = 0.1
    DEFAULT_LDAP_TIMEOUT = 1.0

    def __init__(self, config):
        self._config = config

    def name(self):
        return self._config['name']

    def unique_columns(self):
        return self._config.get(BaseSourcePlugin.UNIQUE_COLUMNS)

    def source_to_display(self):
        return self._config.get(BaseSourcePlugin.SOURCE_TO_DISPLAY)

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
        source_to_display = self._config.get(BaseSourcePlugin.SOURCE_TO_DISPLAY)
        if not source_to_display:
            return None

        attributes = list(source_to_display)
        unique_columns = self._config.get(BaseSourcePlugin.UNIQUE_COLUMNS)
        if unique_columns:
            for column in unique_columns:
                if column not in attributes:
                    attributes.append(column)

        return attributes

    def build_search_filter(self, term):
        # Note that this function might return an invalid filter if the config
        # use an incorrectly written custom filter.
        term_escaped = escape_filter_chars(term)
        if 'ldap_custom_filter' in self._config:
            return self._build_search_filter_from_custom_filter(term_escaped)
        else:
            return self._build_search_filter_from_searched_columns(term_escaped)

    def _build_search_filter_from_custom_filter(self, term_escaped):
        return self._config['ldap_custom_filter'].replace('%Q', term_escaped)

    def _build_search_filter_from_searched_columns(self, term_escaped):
        l = list('(%s=*%s*)' % (attr, term_escaped) for attr in self._config[BaseSourcePlugin.SEARCHED_COLUMNS])
        if len(l) == 1:
            return l[0]
        else:
            return '(|%s)' % ''.join(l)

    def build_list_filter(self, uids):
        # XXX do we need to handle the case were the number of elements in a uid is
        #     not the same as the number of unique column ?
        # XXX do we need to handle the case were a value in the tuple is None or something alike ?
        if not uids:
            return None

        unique_columns = self._config[BaseSourcePlugin.UNIQUE_COLUMNS]

        l = []
        for uid in uids:
            item_l = list('(%s=%s)' % (attr, escape_filter_chars(value)) for (attr, value) in zip(unique_columns, uid))
            if len(item_l) == 1:
                l.append(item_l[0])
            else:
                l.append('(&%s)' % ''.join(item_l))

        if len(l) == 1:
            return l[0]
        else:
            return '(|%s)' % ''.join(l)


class _LDAPClient(object):

    def __init__(self, ldap_config, ldap_obj):
        self._ldap_config = ldap_config
        self._ldap_obj = ldap_obj
        self._base_dn = self._ldap_config.ldap_base_dn()
        self._attributes = self._ldap_config.attributes()
        self._set_options()

    def _set_options(self):
        self._ldap_obj.set_option(ldap.OPT_REFERRALS, 0)
        self._ldap_obj.set_option(ldap.OPT_NETWORK_TIMEOUT, self._ldap_config.ldap_network_timeout())
        self._ldap_obj.set_option(ldap.OPT_TIMEOUT, self._ldap_config.ldap_timeout())

    def bind(self):
        self._ldap_obj.simple_bind_s(self._ldap_config.ldap_username(), self._ldap_config.ldap_password())

    def unbind(self):
        self._ldap_obj.unbind_s()

    def search(self, filter_str):
        return self._ldap_obj.search_s(self._base_dn, ldap.SCOPE_SUBTREE, filter_str, self._attributes)


class _LDAPResultFormatter(object):

    def __init__(self, ldap_config):
        self._SourceResult = make_result_class(ldap_config.name(), ldap_config.unique_columns(), ldap_config.source_to_display())

    def format(self, raw_results):
        results = []
        for _, attrs in raw_results:
            fields = dict((name, values[0]) for name, values in attrs.iteritems())
            results.append(self._SourceResult(fields))

        return results
