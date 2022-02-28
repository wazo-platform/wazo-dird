# Copyright 2019-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from marshmallow import (
    exceptions,
    utils,
    validates_schema,
)
from xivo.mallow import fields
from xivo.mallow.validate import Length, Range, validate_string_dict
from xivo.mallow_helpers import Schema

BaseSchema = Schema


class VerifyCertificateField(fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        if value in (True, 'true', 'True'):
            return True

        if value in (False, 'false', 'False'):
            return False

        try:
            return utils.ensure_text_type(value)
        except UnicodeDecodeError:
            self.make_error('invalid_utf8')


class BaseSourceSchema(BaseSchema):
    uuid = fields.UUID(dump_only=True)
    tenant_uuid = fields.UUID(dump_only=True)
    name = fields.String(validate=Length(min=1, max=512), required=True)
    first_matched_columns = fields.List(
        fields.String(validate=Length(min=1, max=128)), missing=[]
    )
    searched_columns = fields.List(
        fields.String(validate=Length(min=1, max=128)), missing=[]
    )
    format_columns = fields.Dict(validate=validate_string_dict, missing={})


class ConfdConfigSchema(BaseSchema):
    host = fields.String(validate=Length(min=1, max=1024), missing='localhost')
    port = fields.Integer(validate=Range(min=1, max=65535), missing=443)
    https = fields.Boolean(missing=True)
    verify_certificate = VerifyCertificateField(missing=True)
    prefix = fields.String(allow_none=True, missing='/api/confd')
    version = fields.String(validate=Length(min=1, max=16), missing='1.1')
    timeout = fields.Float(validate=Range(min=0, max=3660))


class BaseAuthConfigSchema(BaseSchema):
    host = fields.String(validate=Length(min=1, max=1024), missing='localhost')
    port = fields.Integer(validate=Range(min=1, max=65535), missing=443)
    https = fields.Boolean(missing=True)
    verify_certificate = VerifyCertificateField(missing=True)
    prefix = fields.String(allow_none=True, missing='/api/auth')
    version = fields.String(validate=Length(min=1, max=16), missing='0.1')
    timeout = fields.Float(validate=Range(min=0, max=3660))


class AuthConfigSchema(BaseAuthConfigSchema):
    key_file = fields.String(validate=Length(min=1, max=1024), allow_none=True)
    username = fields.String(validate=Length(min=1, max=512), allow_none=True)
    password = fields.String(validate=Length(min=1, max=512), allow_none=True)

    @validates_schema
    def validate_auth_info(self, data, **kwargs):
        key_file = data.get('key_file')
        username = data.get('username')

        if key_file and username:
            raise exceptions.ValidationError(
                'a "key_file" or a "username" and "password" must be specified'
            )

        if key_file or username:
            return

        raise exceptions.ValidationError(
            'a "key_file" or a "username" and "password" must be specified'
        )
