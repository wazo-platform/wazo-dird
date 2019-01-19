# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo.mallow import fields
from xivo.mallow.validate import Length
from xivo.mallow_helpers import ListSchema as _ListSchema
from wazo_dird.schemas import BaseSourceSchema


class SourceSchema(BaseSourceSchema):
    db_uri = fields.String(validate=Length(min=1, max=256), required=True)


class ListSchema(_ListSchema):

    searchable_columns = ['uuid', 'name', 'db_uri']

    order = fields.WazoOrder(
        sort_columns=['name', 'db_uri'],
        default_sort_column='name',
    )
    recurse = fields.Boolean(missing=False)


source_schema = SourceSchema()
list_schema = ListSchema()
