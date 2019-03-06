# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from time import time
from xivo.rest_api_helpers import APIException


class OldAPIException(Exception):

    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body


class DatabaseServiceUnavailable(Exception):

    def __init__(self):
        super().__init__('Postgresql is unavailable')


class NoSuchDisplay(APIException):

    def __init__(self, display_uuid):
        msg = 'No such display: "{}"'.format(display_uuid)
        details = {
            'uuid': display_uuid,
        }
        super().__init__(404, msg, 'unknown-display', details, 'displays')


class NoSuchFavorite(ValueError):

    def __init__(self, contact_id):
        message = "No such favorite: {}".format(contact_id)
        super().__init__(message)


class NoSuchPhonebook(ValueError):

    def __init__(self, phonebook_id):
        message = 'No such phonebook: {}'.format(phonebook_id)
        super().__init__(message)


class NoSuchProfile(OldAPIException):

    def __init__(self, profile):
        status_code = 404
        body = {
            'reason': ['The profile `{}` does not exist'.format(profile)],
            'timestamp': [time()],
            'status_code': status_code,
        }
        super().__init__(status_code, body)


class NoSuchUser(OldAPIException):

    def __init__(self, user_uuid):
        status_code = 404
        body = {
            'reason': ['The user `{}` does not exist'.format(user_uuid)],
            'timestamp': [time()],
            'status_code': status_code,
        }
        super().__init__(status_code, body)


class NoSuchContact(ValueError):

    def __init__(self, contact_id):
        message = "No such contact: {}".format(contact_id)
        super().__init__(message)


class NoSuchSource(APIException):

    def __init__(self, source_uuid):
        msg = 'No such source: "{}"'.format(source_uuid)
        details = {
            'uuid': source_uuid,
        }
        super().__init__(404, msg, 'unknown-source', details, 'sources')


class NoSuchTenant(ValueError):

    def __init__(self, tenant_name):
        message = 'No such tenant: {}'.format(tenant_name)
        super().__init__(message)


class DuplicatedContactException(Exception):

    _msg = 'Duplicating contact'

    def __init__(self):
        super().__init__(self._msg)


class DuplicatedFavoriteException(Exception):

    pass


class DuplicatedPhonebookException(Exception):

    _msg = 'Duplicating phonebook'

    def __init__(self):
        super().__init__(self._msg)


class DuplicatedSourceException(APIException):

    def __init__(self, name):
        msg = 'The name "{}" is already used'.format(name)
        details = {'name': {'constraint_id': 'unique', 'message': msg}}
        super().__init__(409, 'Conflict detected', 'conflict', details, 'sources')


class ProfileNotFoundError(Exception):

    pass


class InvalidArgumentError(Exception):

    pass


class InvalidConfigError(Exception):

    def __init__(self, location_path, msg):
        super().__init__(location_path, msg)
        self.location_path = location_path
        self.msg = msg


class InvalidPhonebookException(Exception):

    def __init__(self, errors):
        self.errors = errors

    def __str__(self):
        return str(self.errors)


class InvalidContactException(Exception):

    pass
