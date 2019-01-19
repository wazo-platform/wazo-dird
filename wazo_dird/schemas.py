# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from marshmallow import (
    Schema,
    compat,
    pre_load,
    utils,
)
from xivo.mallow import fields
from xivo.mallow.validate import (
    Length,
    validate_string_dict,
)


class BaseSchema(Schema):

    class Meta:
        ordered = True
        strict = True

    @pre_load
    def ensude_dict(self, data):
        return data or {}


class VerifyCertificateField(fields.Field):

    def _deserialize(self, value, attr, data):
        if value in (True, 'true', 'True'):
            return True

        if value in (False, 'false', 'False'):
            return False

        if not isinstance(value, compat.basestring):
            self.fail('invalid')

        try:
            return utils.ensure_text_type(value)
        except UnicodeDecodeError:
            self.fail('invalid_utf8')


class BaseSourceSchema(BaseSchema):
    uuid = fields.UUID(dump_only=True)
    tenant_uuid = fields.UUID(dump_only=True)
    name = fields.String(validate=Length(min=1, max=512))
    first_matched_columns = fields.List(fields.String(validate=Length(min=1, max=128)), missing=[])
    searched_columns = fields.List(fields.String(validate=Length(min=1, max=128)), missing=[])
    format_columns = fields.Dict(validate=validate_string_dict, missing={})
