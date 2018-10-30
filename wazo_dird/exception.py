# Copyright 2015-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+


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
        msg = 'The tenant should be alphanumeric: {}'.format(tenant)
        super(InvalidTenantException, self).__init__(msg)
