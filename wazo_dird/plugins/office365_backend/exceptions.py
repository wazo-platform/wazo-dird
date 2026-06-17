# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Any

from xivo.rest_api_helpers import APIException


class UnexpectedEndpointException(APIException):  # type: ignore[misc]
    code = 503

    def __init__(self, **kwargs: Any) -> None:
        message = 'Unexpected endpoint error.'
        details = kwargs
        super().__init__(self.code, message, 'unexpected-endpoint-error', details)


class MicrosoftTokenNotFoundException(APIException):  # type: ignore[misc]
    code = 404

    def __init__(self, user_uuid: str) -> None:
        message = 'No microsoft token found.'
        details = {'user_uuid': user_uuid}
        super().__init__(self.code, message, 'no-token-found', details)
