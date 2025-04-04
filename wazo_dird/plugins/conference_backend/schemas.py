# Copyright 2019-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from marshmallow import pre_dump
from xivo.mallow import fields
from xivo.mallow_helpers import ListSchema as _ListSchema

from wazo_dird.schemas import (
    AuthConfigSchema,
    BaseSchema,
    BaseSourceSchema,
    ConfdConfigSchema,
)


class ExtensionSchema(BaseSchema):
    context = fields.String()
    exten = fields.String()


class ContactSchema(BaseSchema):
    id = fields.Integer()
    name = fields.String()
    extensions = fields.Nested(ExtensionSchema, many=True)
    incalls = fields.Nested(ExtensionSchema, many=True)

    @pre_dump
    def unpack_extensions(self, data, **kwargs):
        extension_schema = ExtensionSchema(many=True)
        incalls = []

        extensions = extension_schema.dump(data['extensions'])

        for incall in data['incalls']:
            incalls += extension_schema.dump(incall['extensions'])

        data['extensions'] = extensions
        data['incalls'] = incalls

        return data


class ContactListSchema(_ListSchema):
    searchable_columns = ['id', 'name']
    sort_columns = ['name']
    default_sort_column = 'name'

    recurse = fields.Boolean(load_default=False)


class ListSchema(_ListSchema):
    searchable_columns = ['uuid', 'name']
    sort_columns = ['name']
    default_sort_column = 'name'

    recurse = fields.Boolean(load_default=False)


class SourceSchema(BaseSourceSchema):
    auth = fields.Nested(
        AuthConfigSchema, load_default=lambda: AuthConfigSchema().load({})
    )
    confd = fields.Nested(
        ConfdConfigSchema, load_default=lambda: ConfdConfigSchema().load({})
    )


contact_list_schema = ContactSchema(many=True)
contact_list_param_schema = ContactListSchema()
source_schema = SourceSchema()
source_list_schema = SourceSchema(many=True)
list_schema = ListSchema()
