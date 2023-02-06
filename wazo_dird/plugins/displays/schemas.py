# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow import fields
from xivo.mallow_helpers import ListSchema as _ListSchema

from wazo_dird.database.schemas import DisplaySchema


class ListSchema(_ListSchema):
    searchable_columns = ['uuid', 'name']
    sort_columns = ['name']
    default_sort_column = 'name'

    recurse = fields.Boolean(missing=False)


display_list_schema = DisplaySchema(many=True)
display_schema = DisplaySchema()
list_schema = ListSchema()
