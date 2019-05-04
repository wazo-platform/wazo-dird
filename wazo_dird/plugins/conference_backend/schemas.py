# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow import fields
from wazo_dird.schemas import (
    AuthConfigSchema,
    BaseSourceSchema,
    ConfdConfigSchema,
)


class SourceSchema(BaseSourceSchema):
    auth = fields.Nested(AuthConfigSchema, missing={})
    confd = fields.Nested(ConfdConfigSchema, missing={})


source_schema = SourceSchema()
