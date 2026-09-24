# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from marshmallow import EXCLUDE, Schema
from xivo.mallow import fields, validate


class ListSchema(Schema):
    # order is validated against the contacts themselves, in the DAO: personal
    # contact fields are free-form, so there is no column list to validate
    # against here.
    class Meta:
        unknown = EXCLUDE

    limit = fields.Integer(validate=validate.Range(min=1), load_default=None)
    offset = fields.Integer(validate=validate.Range(min=0), load_default=0)


list_schema = ListSchema()
