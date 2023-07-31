from __future__ import annotations

from typing import TypedDict, cast

from marshmallow import fields
from xivo.mallow_helpers import ListSchema

from wazo_dird.utils import projection


class CountParams(TypedDict):
    search: str | None


class ContactListSchema(ListSchema):
    searchable_columns = ['uuid', 'name']
    sort_columns = ['firstname', 'lastname', 'name']
    default_sort_column = 'name'

    recurse = fields.Boolean(missing=False)

    def load_count(self, args: dict, **kwargs) -> CountParams:
        return cast(CountParams, projection(self.load(args, **kwargs), ['search']))


contact_list_schema = ContactListSchema()


class PhonebookListSchema(ListSchema):
    searchable_columns = ['name', 'description']
    sort_columns = ['name', 'description']
    default_sort_column = 'name'

    recurse = fields.Boolean(missing=False)

    def load_count(self, args: dict, **kwargs) -> CountParams:
        return cast(CountParams, projection(self.load(args, **kwargs), ['search']))


phonebook_list_schema = PhonebookListSchema()
