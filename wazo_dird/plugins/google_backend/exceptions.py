# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from xivo.rest_api_helpers import APIException


class GoogleTokenException(APIException):
    """The user has no Google access token that Google accepts"""


class GoogleTokenNotFoundException(GoogleTokenException):
    code = 404

    def __init__(self, user_uuid: str) -> None:
        message = 'No google token found.'
        details = {'user_uuid': user_uuid}
        super().__init__(self.code, message, 'no-token-found', details)


class GoogleTokenRejectedException(GoogleTokenException):
    code = 403

    def __init__(self) -> None:
        message = 'Google rejected the access token.'
        super().__init__(self.code, message, 'google-token-rejected')


class GoogleUnavailableException(APIException):
    code = 503

    def __init__(self) -> None:
        message = 'Google contacts are unavailable.'
        super().__init__(self.code, message, 'google-unavailable')
