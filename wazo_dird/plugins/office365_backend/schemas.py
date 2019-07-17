# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later


from xivo.mallow_helpers import ListSchema as _ListSchema
from wazo_dird.schemas import BaseSourceSchema
from xivo.mallow import fields

from xivo.mallow.validate import Length


class SourceSchema(BaseSourceSchema):

    auth = fields.Dict(
        keys=fields.String(validate=Length(min=1, max=64)),
        values=fields.String(validate=Length(min=1, max=64))
    )
    endpoint = fields.String(
        missing='https://graph.microsoft.com/v1.0/me/contacts',
        validate=Length(min=1, max=255),
    )


class ListSchema(_ListSchema):

    searchable_columns = ['uuid', 'name']
    sort_columns = ['name']
    default_sort_column = 'name'

    recurse = fields.Boolean(missing=False)


source_schema = SourceSchema()
source_list_schema = SourceSchema(many=True)
list_schema = ListSchema()
