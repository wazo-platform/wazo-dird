# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import TypedDict

from marshmallow import post_load
from xivo.mallow import fields
from xivo.mallow_helpers import ListSchema as _ListSchema

from wazo_dird.schemas import BaseSourceSchema


class SourceSchema(BaseSourceSchema):
    phonebook_uuid = fields.UUID(required=True)
    phonebook_name = fields.String(dump_only=True)
    phonebook_description = fields.String(dump_only=True)

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
    searchable_columns: list[str] = []
    sort_columns = ['firstname', 'lastname', 'number']
    default_sort_column = None


contact_list_schema = ContactListSchema()
