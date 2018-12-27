# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo.mallow_helpers import ListSchema as _ListSchema

ListSchema = _ListSchema
ListSchema.searchable_columns = ['name']
