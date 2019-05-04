# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow import fields
from xivo.mallow_helpers import ListSchema as _ListSchema
from wazo_dird.schemas import (
    AuthConfigSchema,
    BaseSourceSchema,
    ConfdConfigSchema,
)


class ListSchema(_ListSchema):

    searchable_columns = ['uuid', 'name']
    sort_columns = ['name']
    default_sort_column = 'name'

    recurse = fields.Boolean(missing=False)


class SourceSchema(BaseSourceSchema):
    auth = fields.Nested(AuthConfigSchema, missing={})
    confd = fields.Nested(ConfdConfigSchema, missing={})


source_schema = SourceSchema()
source_list_schema = SourceSchema(many=True)
list_schema = ListSchema()
