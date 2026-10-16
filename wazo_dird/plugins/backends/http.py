# Copyright 2018-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Any, cast

from flask import request
from marshmallow import ValidationError
from xivo import rest_api_helpers

from wazo_dird.auth import required_acl
from wazo_dird.http import LegacyAuthResource

from .schemas import ListSchema
from .service import BackendService


class Backends(LegacyAuthResource):
    def __init__(self, service: BackendService) -> None:
        self._service = service

    @required_acl('dird.backends.read')
    def get(self) -> dict[str, Any]:
        try:
            list_params = ListSchema().load(request.args)
        except ValidationError as e:
            errors = cast(dict[str, Any], e.messages)
            raise rest_api_helpers.APIException(
                400,
                f'invalid parameters: {", ".join(sorted(errors))}',
                'invalid-data',
                details=errors,
            )

        backends = self._service.list_(**list_params)
        filtered = self._service.count(**list_params)
        total = self._service.count()

        return {'total': total, 'filtered': filtered, 'items': backends}
