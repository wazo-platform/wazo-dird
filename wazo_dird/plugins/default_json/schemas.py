# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.mallow import fields
from xivo.mallow.validate import Range

from wazo_dird.schemas import BaseSchema

MAX_CONTACTS_PER_PAGE = 1000


class ContactListSchema(BaseSchema):
    limit = fields.Integer(
        validate=Range(min=1, max=MAX_CONTACTS_PER_PAGE), load_default=100
    )
    offset = fields.Integer(validate=Range(min=0), load_default=0)


contact_list_schema = ContactListSchema()
