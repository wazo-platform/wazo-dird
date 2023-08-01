# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import TypedDict, cast

from marshmallow import post_load
from xivo.mallow import fields
from xivo.mallow_helpers import ListSchema as _ListSchema

from wazo_dird.schemas import BaseSourceSchema
from wazo_dird.utils import projection


class SourceSchema(BaseSourceSchema):
    phonebook_uuid = fields.UUID(required=True)

    @post_load
    def stringify_uuid(self, data, **kwargs):
        data.update(phonebook_uuid=str(data['phonebook_uuid']))
        return data


class ListSchema(_ListSchema):
    searchable_columns = ['uuid', 'name']
    sort_columns = ['name']
    default_sort_column = 'name'

    recurse = fields.Boolean(missing=False)


source_list_schema = SourceSchema(many=True)
source_schema = SourceSchema()
list_schema = ListSchema()


class CountParams(TypedDict):
    search: str | None


class ContactListSchema(_ListSchema):
    searchable_columns = ['uuid', 'firstname', 'lastname']
    sort_columns = ['firstname', 'lastname']
    default_sort_column = 'lastname'

    def load_count(self, args: dict, **kwargs) -> CountParams:
        return cast(CountParams, projection(self.load(args, **kwargs), ['search']))


contact_list_schema = ContactListSchema()
