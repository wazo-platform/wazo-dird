# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo.mallow import fields
from xivo.mallow.validate import (
    Length,
    Range,
    OneOf,
)
from xivo.mallow_helpers import ListSchema as _ListSchema
from wazo_dird.schemas import BaseSourceSchema


class SourceSchema(BaseSourceSchema):
    ldap_uri = fields.String(validate=Length(min=1, max=256), required=True)
    ldap_base_dn = fields.String(validate=Length(min=1, max=1024), required=True)
    ldap_username = fields.String(validate=Length(min=1), missing=None)
    ldap_password = fields.String(validate=Length(min=1), missing=None)
    ldap_custom_filter = fields.String(validate=Length(min=1, max=1024), missing=None)
    ldap_network_timeout = fields.Float(validate=Range(min=0), default=0.3)
    ldap_timeout = fields.Float(validate=Range(min=0), default=1.0)
    unique_column = fields.String(Length(min=1, max=128), allownone=True, missing=None)
    unique_column_format = fields.String(validate=OneOf('string', 'binary_uuid'), missing='string')


class ListSchema(_ListSchema):

    searchable_columns = ['uuid', 'name', 'ldap_uri', 'ldap_base_dn', 'ldap_username']

    order = fields.WazoOrder(
        sort_columns=['name', 'ldap_uri', 'ldap_base_dn', 'ldap_username'],
        default_sort_column='name',
    )
    recurse = fields.Boolean(missing=False)


source_list_schema = SourceSchema(many=True)
source_schema = SourceSchema()
list_schema = ListSchema()
