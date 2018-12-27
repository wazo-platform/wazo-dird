# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo.mallow import fields
from xivo.mallow_helpers import ListSchema as _ListSchema


class ListSchema(_ListSchema):

    searchable_columns = ['name']

    order = fields.WazoOrder(
        sort_columns=['name'],
        default_sort_column='name',
    )
