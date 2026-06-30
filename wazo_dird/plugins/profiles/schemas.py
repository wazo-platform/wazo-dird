# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Any

from marshmallow import RAISE
from xivo.mallow import fields
from xivo.mallow.validate import Length, Range
from xivo.mallow_helpers import ListSchema as _ListSchema

from wazo_dird.schemas import BaseSchema


class ResourceSchema(BaseSchema):
    uuid = fields.UUID(required=True)


class ServiceOptionsSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        unknown = RAISE

    timeout = fields.Float(
        load_default=None, allow_none=True, validate=Range(min=0, min_inclusive=False)
    )


class ServiceConfigSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        unknown = RAISE

    sources = fields.Nested(ResourceSchema, many=True, load_default=[])
    options = fields.Nested(ServiceOptionsSchema, load_default={})


class ServiceDictSchema(fields.Nested):
    # marshmallow names _serialize's first arg "value" in Field but
    # "nested_obj" in Nested; an override can't match both names.
    def _serialize(  # type: ignore[override]
        self, nested_obj: Any, attr: str | None, obj: Any, **kwargs: Any
    ) -> dict[str, Any] | None:
        if nested_obj is None:
            return None

        result: dict[str, Any] = {}
        for service_name, service_config in nested_obj.items():
            result[service_name] = ServiceConfigSchema().dump(service_config)
        return result

    def _deserialize(  # type: ignore[override]
        self,
        nested_obj: Any,
        attr: str | None,
        obj: Any,
        partial: bool | tuple[str, ...] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        if nested_obj is None:
            return None

        result: dict[str, Any] = {}
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

    recurse = fields.Boolean(load_default=False)


list_schema = ListSchema()
profile_list_schema = ProfileSchema(many=True)
profile_schema = ProfileSchema()
