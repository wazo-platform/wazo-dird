# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow import fields
from xivo.mallow_helpers import ListSchema as _ListSchema

from wazo_dird.database.schemas import SourceSchema


class ListSchema(_ListSchema):
    searchable_columns = ['uuid', 'backend', 'name']
    sort_columns = ['name', 'backend']
    default_sort_column = 'name'

    recurse = fields.Boolean(missing=False)


source_list_schema = SourceSchema(many=True)
list_schema = ListSchema()
