# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow import fields
from xivo.mallow.validate import Length, Range
from xivo.mallow_helpers import ListSchema as _ListSchema
from wazo_dird.schemas import BaseSourceSchema, VerifyCertificateField


class SourceSchema(BaseSourceSchema):
    lookup_url = fields.URL(required=True)
    list_url = fields.URL(allownone=True, missing=None)
    verify_certificate = VerifyCertificateField(missing=True)
    delimiter = fields.String(Length(min=1, max=1), missing=',')
    timeout = fields.Float(Range(min=0), missing=10.0)
    unique_column = fields.String(Length(min=1, max=128), allownone=True, missing=None)


class ListSchema(_ListSchema):

    searchable_columns = ['uuid', 'name', 'lookup_url', 'list_url']
    sort_columns = ['name', 'lookup_url', 'list_url']
    default_sort_column = 'name'

    recurse = fields.Boolean(missing=False)


source_list_schema = SourceSchema(many=True)
source_schema = SourceSchema()
list_schema = ListSchema()
