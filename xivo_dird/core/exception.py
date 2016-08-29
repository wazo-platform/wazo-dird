# -*- coding: utf-8 -*-

# Copyright (C) 2015-2016 Avencall
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


class DatabaseServiceUnavailable(Exception):

    def __init__(self):
        super(DatabaseServiceUnavailable, self).__init__('Postgresql is unavailable')


class NoSuchFavorite(ValueError):

    def __init__(self, contact_id):
        message = "No such favorite: {}".format(contact_id)
        super(NoSuchFavorite, self).__init__(message)


class NoSuchPhonebook(ValueError):

    def __init__(self, phonebook_id):
        message = 'No such phonebook: {}'.format(phonebook_id)
        super(NoSuchPhonebook, self).__init__(message)


class NoSuchContact(ValueError):

    def __init__(self, contact_id):
        message = "No such contact: {}".format(contact_id)
        super(NoSuchContact, self).__init__(message)


class DuplicatedContactException(Exception):

    _msg = 'Duplicating contact'

    def __init__(self):
        super(DuplicatedContactException, self).__init__(self._msg)


class DuplicatedFavoriteException(Exception):

    pass


class DuplicatedPhonebookException(Exception):

    _msg = 'Duplicating phonebook'

    def __init__(self):
        super(DuplicatedPhonebookException, self).__init__(self._msg)


class ProfileNotFoundError(Exception):

    pass


class InvalidArgumentError(Exception):

    pass


class InvalidConfigError(Exception):

    def __init__(self, location_path, msg):
        super(InvalidConfigError, self).__init__(location_path, msg)
        self.location_path = location_path
        self.msg = msg


class InvalidPhonebookException(Exception):

    def __init__(self, errors):
        self.errors = errors

    def __str__(self):
        return str(self.errors)


class InvalidContactException(Exception):

    pass


class InvalidTenantException(Exception):

    def __init__(self, tenant):
        msg = u'The tenant should be alphanumeric: {}'.format(tenant)
        super(InvalidTenantException, self).__init__(msg)
