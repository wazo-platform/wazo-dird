# Copyright 2019-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow import fields
from xivo.mallow.validate import Length, OneOf, Range
from xivo.mallow_helpers import ListSchema as _ListSchema

from wazo_dird.schemas import BaseSourceSchema


class SourceSchema(BaseSourceSchema):
    ldap_uri = fields.String(validate=Length(min=1, max=256), required=True)
    ldap_base_dn = fields.String(validate=Length(min=1, max=1024), required=True)
    ldap_username = fields.String(validate=Length(min=1), load_default=None)
    ldap_password = fields.String(validate=Length(min=1), load_default=None)
    ldap_custom_filter = fields.String(
        validate=Length(min=1, max=1024), load_default=None
    )
    ldap_network_timeout = fields.Float(validate=Range(min=0), dump_default=0.3)
    ldap_timeout = fields.Float(validate=Range(min=0), dump_default=1.0)
    unique_column = fields.String(
        validate=Length(min=1, max=128), allow_none=True, load_default=None
    )
    unique_column_format = fields.String(
        validate=OneOf(['string', 'binary_uuid']), load_default='string'
    )


class ListSchema(_ListSchema):
    searchable_columns = ['uuid', 'name', 'ldap_uri', 'ldap_base_dn', 'ldap_username']
    sort_columns = ['name', 'ldap_uri', 'ldap_base_dn', 'ldap_username']
    default_sort_column = 'name'

    recurse = fields.Boolean(load_default=False)


source_list_schema = SourceSchema(many=True)
source_schema = SourceSchema()
list_schema = ListSchema()
