# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.rest_api_helpers import APIException


class GoogleTokenNotFoundException(APIException):

    code = 404

    def __init__(self, user_uuid):
        message = 'No google token found.'
        details = {
            'user_uuid': user_uuid,
        }
        super().__init__(self.code, message, 'no-token-found', details)
