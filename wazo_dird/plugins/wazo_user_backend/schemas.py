# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from marshmallow import (
    compat,
    exceptions,
    utils,
    validates_schema,
)
from xivo.mallow import fields
from xivo.mallow.validate import (
    Length,
    Range,
)
from xivo.mallow_helpers import ListSchema as _ListSchema
from wazo_dird.schemas import (
    BaseSchema,
    BaseSourceSchema,
)


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


class _ConfdConfigSchema(BaseSchema):
    host = fields.String(validate=Length(min=1, max=1024), missing='localhost')
    port = fields.Integer(validate=Range(min=1, max=65535), missing=9486)
    verify_certificate = _VerifyCertificateField(missing=True)
    timeout = fields.Float(validate=Range(min=0, max=3660))
    https = fields.Boolean(missing=True)
    version = fields.String(validate=Length(min=1, max=16), missing='1.1')


class _AuthConfigSchema(BaseSchema):
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
        key_file = data.get('key_file')
        username = data.get('username')

        if key_file and username:
            raise exceptions.ValidationError(
                'a "key_file" or a "username" and "password" must be specified',
            )

        if key_file or username:
            return

        raise exceptions.ValidationError(
            'a "key_file" or a "username" and "password" must be specified',
        )


class SourceSchema(BaseSourceSchema):
    auth = fields.Nested(_AuthConfigSchema, missing={})
    confd = fields.Nested(_ConfdConfigSchema, missing={})


class ListSchema(_ListSchema):

    searchable_columns = ['uuid', 'name']

    order = fields.WazoOrder(
        sort_columns=['name'],
        default_sort_column='name',
    )
    recurse = fields.Boolean(missing=False)


source_schema = SourceSchema()
list_schema = ListSchema()
