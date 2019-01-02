# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from marshmallow import (
    compat,
    exceptions,
    Schema,
    pre_load,
    utils,
    validates_schema,
)
from xivo.mallow import fields
from xivo.mallow.validate import (
    Length,
    Range,
    validate_string_dict,
)


class _BaseSchema(Schema):

    class Meta:
        ordered = True
        strict = True

    @pre_load
    def ensude_dict(self, data):
        return data or {}


class _VerifyCertificateField(fields.Field):

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


class _ConfdConfigSchema(_BaseSchema):
    host = fields.String(validate=Length(min=1, max=1024), missing='localhost')
    port = fields.Integer(validate=Range(min=1, max=65535), missing=9486)
    verify_certificate = _VerifyCertificateField(missing=True)
    timeout = fields.Float(validate=Range(min=0, max=3660))
    https = fields.Boolean(missing=True)
    version = fields.String(validate=Length(min=1, max=16), missing='1.1')


class _AuthConfigSchema(_BaseSchema):
    host = fields.String(validate=Length(min=1, max=1024), missing='localhost')
    port = fields.Integer(validate=Range(min=1, max=65535), missing=9497)
    key_file = fields.String(validate=Length(min=1, max=1024), allow_none=True)
    username = fields.String(validate=Length(min=1, max=512), allow_none=True)
    password = fields.String(validate=Length(min=1, max=512), allow_none=True)
    verify_certificate = _VerifyCertificateField(missing=True)
    timeout = fields.Float(validate=Range(min=0, max=3660))
    version = fields.String(validate=Length(min=1, max=16), missing='0.1')

    @validates_schema
    def validate_auth_info(self, data):
        if data.get('key_file'):
            return
        if data.get('username') and data.get('password'):
            return

        raise exceptions.ValidationError(
            'a "key_file" and a "username" and "password" must be specified',
        )


class SourceSchema(_BaseSchema):
    uuid = fields.UUID(dump_only=True)
    tenant_uuid = fields.UUID(dump_only=True)
    name = fields.String(validate=Length(min=1, max=512))
    first_matched_columns = fields.List(fields.String(validate=Length(min=1, max=128)), missing=[])
    searched_columns = fields.List(fields.String(validate=Length(min=1, max=128)), missing=[])
    format_columns = fields.Dict(validate=validate_string_dict, missing={})
    auth = fields.Nested(_AuthConfigSchema, missing={})
    confd = fields.Nested(_ConfdConfigSchema, missing={})


source_schema = SourceSchema()
