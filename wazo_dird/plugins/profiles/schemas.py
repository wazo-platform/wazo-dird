# Copyright 2019-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow import fields
from xivo.mallow.validate import Length
from xivo.mallow_helpers import ListSchema as _ListSchema
from wazo_dird.schemas import BaseSchema


class ResourceSchema(BaseSchema):
    uuid = fields.UUID(required=True)


class ServiceConfigSchema(BaseSchema):
    sources = fields.Nested(ResourceSchema, many=True, missing=[])
    options = fields.Dict(missing={})


class ServiceDictSchema(fields.Nested):
    def _serialize(self, nested_obj, attr, obj, **_):
        if nested_obj is None:
            return None

        result = {}
        for service_name, service_config in nested_obj.items():
            result[service_name] = ServiceConfigSchema().dump(service_config)
        return result

    def _deserialize(self, nested_obj, attr, obj, **kwargs):
        if nested_obj is None:
            return None

        result = {}
        for service_name, service_config in nested_obj.items():
            result[service_name] = ServiceConfigSchema().load(service_config)
        return result


class ProfileSchema(BaseSchema):

    uuid = fields.UUID(dump_only=True)
    tenant_uuid = fields.UUID(dump_only=True)
    name = fields.String(validate=Length(min=1, max=512), required=True)
    display = fields.Nested(ResourceSchema)
    services = ServiceDictSchema(BaseSchema, required=True)


class ListSchema(_ListSchema):

    searchable_columns = ['uuid', 'name']
    sort_columns = ['name']
    default_sort_column = 'name'

    recurse = fields.Boolean(missing=False)


list_schema = ListSchema()
profile_list_schema = ProfileSchema(many=True)
profile_schema = ProfileSchema()
