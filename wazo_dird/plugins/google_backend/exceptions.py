# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Any

from xivo.rest_api_helpers import APIException


class GoogleTokenNotFoundException(APIException):
    code = 404

    def __init__(self, user_uuid: str) -> None:
        message = 'No google token found.'
        details = {'user_uuid': user_uuid}
        super().__init__(self.code, message, 'no-token-found', details)


class GoogleUnavailableException(APIException):
    code = 503

    def __init__(self, **details: Any) -> None:
        message = 'Google contacts are unavailable.'
        super().__init__(self.code, message, 'google-unavailable', details)
