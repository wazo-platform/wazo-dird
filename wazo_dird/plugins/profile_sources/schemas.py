# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later


from xivo.mallow_helpers import ListSchema as _ListSchema


class ListSchema(_ListSchema):
    searchable_columns = ['uuid', 'name', 'backend']
    sort_columns = ['name', 'backend']
    default_sort_column = 'name'
