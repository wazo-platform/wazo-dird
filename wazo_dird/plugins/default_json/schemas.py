# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from xivo.mallow import fields
from xivo.mallow.validate import Length
from xivo.mallow_helpers import Schema


class LookupQueryStringSchema(Schema):
    # An empty term matches every entry of every source configured on the
    # profile, so a lookup without a term is a full directory dump rather than
    # a search: reject it instead of fanning out.
    term = fields.String(required=True, validate=Length(min=1))


lookup_query_string_schema = LookupQueryStringSchema()
