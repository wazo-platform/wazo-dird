# Copyright 2019-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow import fields
from xivo.mallow.validate import Length
from xivo.mallow_helpers import ListSchema as _ListSchema

from wazo_dird.schemas import BaseSourceSchema


class SourceSchema(BaseSourceSchema):
    unique_column = fields.String(
        validate=Length(min=1, max=128),
        allow_none=True,
        load_default=None,
    )
    file = fields.String(validate=Length(min=1), required=True)
    separator = fields.String(validate=Length(min=1, max=1), load_default=',')


class ListSchema(_ListSchema):
    searchable_columns = ['uuid', 'name', 'file']
    sort_columns = ['name', 'file']
    default_sort_column = 'name'

    recurse = fields.Boolean(load_default=False)


source_list_schema = SourceSchema(many=True)
source_schema = SourceSchema()
list_schema = ListSchema()
