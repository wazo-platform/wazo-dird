# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow import fields
from wazo_dird.schemas import (
    BaseSchema,
)


class DisplayColumnSchema(BaseSchema):
    field = fields.String()
    title = fields.String()
    type = fields.String()
    default = fields.String()
    number_display = fields.String()


class DisplaySchema(BaseSchema):
    uuid = fields.UUID(dump_only=True)
    tenant_uuid = fields.UUID(dump_only=True)
    name = fields.String()
    columns = fields.Nested(DisplayColumnSchema, many=True)


class SourceSchema(BaseSchema):
    uuid = fields.UUID(dump_only=True)
    tenant_uuid = fields.UUID(dump_only=True)
    name = fields.String()
    backend = fields.String()


class ServiceSchema(BaseSchema):
    sources = fields.Nested(SourceSchema, many=True)


class ServiceDictSchema(fields.Nested):

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None

        result = {}
        for profile_service in value:
            service_name = profile_service.service.name
            result[service_name] = profile_service.config
            sources = SourceSchema().dump(profile_service.sources, many=True).data
            result[service_name]['sources'] = sources
        return result


class ProfileSchema(BaseSchema):
    uuid = fields.UUID(dump_only=True)
    tenant_uuid = fields.UUID(dump_only=True)
    name = fields.String()
    display = fields.Nested(DisplaySchema)
    services = ServiceDictSchema(BaseSchema, required=True)
