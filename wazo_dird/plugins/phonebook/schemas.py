from xivo.mallow_helpers import ListSchema

from marshmallow import fields


def project(m: dict, keys: list[str], default=None) -> dict:
    return {k: m.get(k, default) for k in keys}


class ContactListSchema(ListSchema):
    searchable_columns = ['uuid', 'name']
    sort_columns = ['firstname', 'lastname', 'name']
    default_sort_column = 'name'

    recurse = fields.Boolean(missing=False)

    def count(self, args: dict, **kwargs) -> dict:
        return project(self.load(args, **kwargs), ['search'])


contact_list_schema = ContactListSchema()


class PhonebookListSchema(ListSchema):
    searchable_columns = ['name', 'description']
    sort_columns = ['name', 'description']
    default_sort_column = 'name'

    recurse = fields.Boolean(missing=False)

    def count(self, args: dict, **kwargs) -> dict:
        return project(self.load(args, **kwargs), ['search'])


phonebook_list_schema = PhonebookListSchema()
