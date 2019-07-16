# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow_helpers import ListSchema as _ListSchema
from xivo.mallow.validate import Range
from wazo_dird.schemas import (
    BaseSchema,
    BaseSourceSchema,
    VerifyCertificateField,
)
from xivo.mallow import fields

from xivo.mallow.validate import Length


class _AuthConfigSchema(BaseSchema):

    host = fields.String(validate=Length(min=1, max=1024), missing='localhost')
    port = fields.Integer(validate=Range(min=1, max=65535), missing=9497)
    verify_certificate = VerifyCertificateField(missing=True)
    timeout = fields.Float(validate=Range(min=0, max=3660))
    version = fields.String(validate=Length(min=1, max=16), missing='0.1')


class SourceSchema(BaseSourceSchema):

    auth = fields.Nested(_AuthConfigSchema, missing={})


class ListSchema(_ListSchema):

    searchable_columns = ['uuid', 'name']
    sort_columns = ['name']
    default_sort_column = 'name'

    recurse = fields.Boolean(missing=False)


class ContactListSchema(_ListSchema):

    searchable_columns = ['name']
    sort_columns = ['name']
    default_sort_column = 'name'


source_schema = SourceSchema()
source_list_schema = SourceSchema(many=True)
list_schema = ListSchema()
contact_list_schema = ContactListSchema()
