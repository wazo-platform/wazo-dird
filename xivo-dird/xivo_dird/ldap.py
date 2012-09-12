# XiVO CTI Server

# Copyright (C) 2007-2012  Avencall
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
from urllib import unquote
from urlparse import urlparse

logger = logging.getLogger('ldap')


class XivoLDAP(object):
    def __init__(self, iuri):
        self.iuri = iuri
        self.ldapobj = None
        self.uri = None
        self.dbname = None

        try:
            logger.info('LDAP URI requested: %r', iuri)

            if isinstance(iuri, unicode):
                parsed_uri = urlparse(iuri.encode('utf8'))
            else:
                parsed_uri = urlparse(iuri)

            uri_scheme = parsed_uri.scheme
            if uri_scheme not in ('ldap', 'ldaps'):
                raise NotImplementedError('Unknown URI scheme: %r' % uri_scheme)

            # user, pass, host, port
            if parsed_uri.username is None:
                ldapuser = ''
            else:
                # Need to escape backslashes in order for ldap to correctly bind. Related bug #3617.
                ldapuser = parsed_uri.username.replace('\\', '\\\\')

            if parsed_uri.password is None:
                ldappass = ''
            else:
                ldappass = parsed_uri.password

            if parsed_uri.hostname is None:
                ldaphost = 'localhost'
            else:
                ldaphost = parsed_uri.hostname

            if parsed_uri.port is None:
                if uri_scheme == 'ldaps':
                    ldapport = '636'
                else:
                    ldapport = '389'
            else:
                ldapport = parsed_uri.port

            split_path = parsed_uri.path.split('?')
            self.dbname = split_path.pop(0).lstrip('/')

            # ?attributes?scope?filter?extensions = 'asfe'
            while len(split_path) < 4:
                split_path.append('')
            (self.base_attributes, self.base_scope,
             self.base_filter, self.base_extensions) = split_path 
            self.base_filter = unquote(self.base_filter)

            self.uri = "%s://%s:%s" % (uri_scheme, ldaphost, ldapport)
            debuglevel = 0
            self.ldapobj = ldap.initialize(self.uri, debuglevel)
            logger.info('LDAP URI understood: %r / filter: %r', self.uri, self.base_filter)

            self.ldapobj.set_option(ldap.OPT_NETWORK_TIMEOUT, 0.1)

            if not self.ldapobj:
                logger.warning('LDAP SERVER not responding')
                self.ldapobj = None
                return

            self.ldapobj.simple_bind_s(ldapuser, ldappass)
            logger.info('LDAP : simple bind done on %r', ldapuser)

            usetls = False
            if usetls:
                self.ldapobj.set_option(ldap.OPT_X_TLS, 1)

        except ldap.LDAPError, exc:
            logger.exception('__init__: ldap.LDAPError (%r, %r, %r)', self.ldapobj, iuri, exc)
            self.ldapobj = None

    def getldap(self, search_filter, search_attributes, searchpattern):
        if self.ldapobj is None:
            self.__init__(self.iuri)

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
                             self.ldapobj, self.uri, exc1)
            self.__init__(self.iuri)
            result = []
            try:
                if self.ldapobj is not None:
                    result = self.ldapobj.search_s(self.dbname,
                                                   ldap.SCOPE_SUBTREE,
                                                   actual_filter,
                                                   search_attributes)
            except ldap.LDAPError, exc2:
                logger.exception('getldap: ldap.LDAPError (%r, %r, %r) could not reconnect',
                                 self.ldapobj, self.uri, exc2)
            finally:
                return result
