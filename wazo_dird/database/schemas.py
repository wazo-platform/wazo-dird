# Copyright 2019-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import marshmallow

from xivo.mallow import fields
from xivo.mallow.validate import Length
from wazo_dird.schemas import BaseSchema


class DisplayColumnSchema(BaseSchema):
    field = fields.String(allow_none=True)
    title = fields.String(allow_none=True)
    type = fields.String(allow_none=True)
    default = fields.String(allow_none=True)
    number_display = fields.String(allow_none=True)

    @marshmallow.validates_schema
    def check_not_empty(self, data, **kwargs):
        if not data:
            raise marshmallow.ValidationError('Empty columns are now allowed')


class DisplaySchema(BaseSchema):
    uuid = fields.UUID(dump_only=True)
    tenant_uuid = fields.UUID(dump_only=True)
    name = fields.String(validate=Length(min=1, max=512), required=True)
    columns = fields.Nested(
        DisplayColumnSchema,
        many=True,
        required=True,
        validate=Length(min=1),
    )


class SourceSchema(BaseSchema):
    backend = fields.String()
    name = fields.String()
    tenant_uuid = fields.UUID(dump_only=True)
    uuid = fields.UUID(dump_only=True)


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
            sources = SourceSchema().dump(profile_service.sources, many=True)
            result[service_name]['sources'] = sources
        return result


class ProfileSchema(BaseSchema):
    uuid = fields.UUID(dump_only=True)
    tenant_uuid = fields.UUID(dump_only=True)
    name = fields.String()
    display = fields.Nested(DisplaySchema)
    services = ServiceDictSchema(BaseSchema, required=True)
