# -*- coding: utf-8 -*-

# Copyright (C) 2007-2013 Avencall
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

from __future__ import absolute_import

import ldap
import logging

logger = logging.getLogger('ldap')


class XivoLDAP(object):

    def __init__(self, config):
        self.config = config
        self.ldapobj = None
        self.dbname = None

        try:
            logger.info('LDAP config requested: %s', self.config)
            self.ldapobj = self._create_ldap_obj(self.config)
            self._set_filter_properties(config)
            self._perform_bind()
        except ldap.LDAPError, exc:
            logger.exception('__init__: ldap.LDAPError (%r, %r, %r)', self.ldapobj, self.config, exc)
            self.ldapobj = None

    def _create_ldap_obj(self, config):
        ldapobj = ldap.initialize(config['uri'], 0)
        ldapobj.set_option(ldap.OPT_REFERRALS, 0)
        ldapobj.set_option(ldap.OPT_NETWORK_TIMEOUT, 0.1)
        ldapobj.set_option(ldap.OPT_TIMEOUT, 1)
        return ldapobj

    def _set_filter_properties(self, config):
        self.dbname = config['basedn']
        self.base_attributes = None
        self.base_scope = None
        self.base_extensions = None
        self.base_filter = config['filter']

    def _perform_bind(self):
        if not self.ldapobj:
            logger.warning('LDAP SERVER not responding')
            self.ldapobj = None
            return

        try:
            self.ldapobj.simple_bind_s(self.config['username'], self.config['password'])
            logger.info('LDAP : simple bind done with %(username)s on %(uri)s', self.config)
        except ldap.INVALID_CREDENTIALS:
            logger.info('LDAP : simple bind failed with %(username)s on %(uri)s : invalid credentials!', self.config)

        usetls = False
        if usetls:
            self.ldapobj.set_option(ldap.OPT_X_TLS, 1)

    def getldap(self, search_filter, search_attributes, searchpattern):
        if self.ldapobj is None:
            self.__init__(self.config)

        if self.base_filter:
            actual_filter = '(&(%s)%s)' % (self.base_filter.replace('%Q', searchpattern),
                                           search_filter)
        else:
            actual_filter = search_filter

        if self.base_scope:
            try:
                actual_scope = getattr(ldap, 'SCOPE_%s' % self.base_scope.upper())
            except AttributeError:
                actual_scope = ldap.SCOPE_SUBTREE
        else:
            actual_scope = ldap.SCOPE_SUBTREE

        logger.info('getldap : performing a request with scope %s, filter %s and attribute %s',
                    actual_scope, actual_filter, search_attributes)

        try:
            result = self.ldapobj.search_s(self.dbname,
                                           actual_scope,
                                           actual_filter,
                                           search_attributes)
            return result
        except (AttributeError, ldap.LDAPError), exc1:
            # display exc1 since sometimes the error stack looks too long for the logfile
            logger.exception('getldap: ldap.LDAPError (%r, %r, %r) retrying to connect',
                             self.ldapobj, self.config, exc1)
            self.__init__(self.config)
            result = []
            try:
                if self.ldapobj is not None:
                    result = self.ldapobj.search_s(self.dbname,
                                                   ldap.SCOPE_SUBTREE,
                                                   actual_filter,
                                                   search_attributes)
            except ldap.LDAPError, exc2:
                logger.exception('getldap: ldap.LDAPError (%r, %r, %r) could not reconnect',
                                 self.ldapobj, self.config, exc2)
            finally:
                return result
