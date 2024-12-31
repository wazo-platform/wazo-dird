# Copyright 2019-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow import fields
from xivo.mallow.validate import Length
from xivo.mallow_helpers import ListSchema as _ListSchema

from wazo_dird.schemas import BaseAuthConfigSchema, BaseSourceSchema


class SourceSchema(BaseSourceSchema):
    auth = fields.Nested(
        BaseAuthConfigSchema,
        load_default=lambda: BaseAuthConfigSchema().load({}),
    )
    endpoint = fields.String(
        load_default='https://graph.microsoft.com/v1.0/me/contacts',
        validate=Length(min=1, max=255),
    )


class ListSchema(_ListSchema):
    searchable_columns = ['uuid', 'name']
    sort_columns = ['name']
    default_sort_column = 'name'

    recurse = fields.Boolean(load_default=False)


class ContactListSchema(_ListSchema):
    searchable_columns = ['displayName', 'givenName', 'surname']
    sort_columns = ['displayName', 'givenName', 'surname']
    default_sort_column = 'displayName'


source_schema = SourceSchema()
source_list_schema = SourceSchema(many=True)
list_schema = ListSchema()
contact_list_schema = ContactListSchema()
