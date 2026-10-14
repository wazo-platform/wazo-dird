# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from marshmallow import fields
from xivo.mallow_helpers import ListSchema as _ListSchema


class ListSchema(_ListSchema):
    # order is validated after loading: the valid columns are not known here
    def _set_order_parameters(self, field_obj: fields.Field) -> None:
        field_obj.load_default = None
        field_obj.allow_none = True


list_schema = ListSchema()
