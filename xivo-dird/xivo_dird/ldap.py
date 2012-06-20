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

import ldap
import logging
from urllib import unquote
from xivo import urisup

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
                ldapuri = urisup.uri_help_split(iuri.encode('utf8'))
            else:
                ldapuri = urisup.uri_help_split(iuri)

            uri_scheme = ldapuri[0]
            if uri_scheme not in ('ldap', 'ldaps'):
                raise NotImplementedError('Unknown URI scheme: %r' % uri_scheme)

            # user, pass, host, port
            if ldapuri[1][0] is None:
                ldapuser = ''
            else:
                ldapuser = ldapuri[1][0]

            if ldapuri[1][1] is None:
                ldappass = ''
            else:
                ldappass = ldapuri[1][1]

            if ldapuri[1][2] is None:
                ldaphost = 'localhost'
            else:
                ldaphost = ldapuri[1][2]

            if ldapuri[1][3] is None:
                if uri_scheme == 'ldaps':
                    ldapport = '636'
                else:
                    ldapport = '389'
            else:
                ldapport = ldapuri[1][3]

            # dbname
            if ldapuri[2] is not None:
                if ldapuri[2].startswith('/'):
                    self.dbname = ldapuri[2][1:]
                else:
                    self.dbname = ldapuri[2]

            dbpos = iuri.rfind(self.dbname)
            # ?attributes?scope?filter?extensions = 'asfe'
            asfe = iuri[dbpos + len(self.dbname):].split('?', 4)
            while len(asfe) < 5:
                asfe.append('')
            (self.base_attributes, self.base_scope,
             self.base_filter, self.base_extensions) = asfe[1:]
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
