# Copyright 2018-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow_helpers import ListSchema as _ListSchema


class ListSchema(_ListSchema):
    searchable_columns = ['name']
    sort_columns = ['name']
    default_sort_column = 'name'
