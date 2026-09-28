# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow import fields
from xivo.mallow.validate import ContainsOnly, Length
from xivo.mallow_helpers import ListSchema as _ListSchema

from wazo_dird.schemas import (
    AuthConfigSchema,
    BaseSchema,
    BaseSourceSchema,
    ConfdConfigSchema,
)

# confd resolves these two as exact-match filters, against an index. A reverse
# lookup on any other column has no meaning in the confd data model, so the
# source refuses it rather than searching and discarding.
FIRST_MATCHED_COLUMNS = ['exten', 'mobile_phone_number']


class SourceSchema(BaseSourceSchema):
    first_matched_columns = fields.List(
        fields.String(validate=Length(min=1, max=128)),
        validate=ContainsOnly(FIRST_MATCHED_COLUMNS),
        load_default=[],
    )
    auth = fields.Nested(
        AuthConfigSchema, load_default=lambda: AuthConfigSchema().load({})
    )
    confd = fields.Nested(
        ConfdConfigSchema, load_default=lambda: ConfdConfigSchema().load({})
    )


class ListSchema(_ListSchema):
    searchable_columns = ['uuid', 'name']
    sort_columns = ['name']
    default_sort_column = 'name'

    recurse = fields.Boolean(load_default=False)


class ContactListSchema(_ListSchema):
    searchable_columns = ['uuid', 'firstname', 'lastname']
    sort_columns = ['firstname', 'lastname']
    default_sort_column = 'firstname'

    recurse = fields.Boolean(load_default=False)
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
