# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow import fields
from xivo.mallow_helpers import ListSchema as _ListSchema

from wazo_dird.schemas import (
    AuthConfigSchema,
    BaseSchema,
    BaseSourceSchema,
    ConfdConfigSchema,
)


class SourceSchema(BaseSourceSchema):
    auth = fields.Nested(AuthConfigSchema, missing=lambda: AuthConfigSchema().load({}))
    confd = fields.Nested(
        ConfdConfigSchema, missing=lambda: ConfdConfigSchema().load({})
    )


class ListSchema(_ListSchema):
    searchable_columns = ['uuid', 'name']
    sort_columns = ['name']
    default_sort_column = 'name'

    recurse = fields.Boolean(missing=False)


class ContactListSchema(_ListSchema):
    searchable_columns = ['uuid', 'firstname', 'lastname']
    sort_columns = ['firstname', 'lastname']
    default_sort_column = 'firstname'

    recurse = fields.Boolean(missing=False)
    uuid = fields.String()


class ContactSchema(BaseSchema):
    id = fields.Integer()
    uuid = fields.String()
    firstname = fields.String()
    lastname = fields.String()
    email = fields.String()
    exten = fields.String()
    mobile_phone_number = fields.String()
    voicemail_number = fields.String()


contact_list_param_schema = ContactListSchema()
contact_list_schema = ContactSchema(many=True)
source_schema = SourceSchema()
source_list_schema = SourceSchema(many=True)
list_schema = ListSchema()
