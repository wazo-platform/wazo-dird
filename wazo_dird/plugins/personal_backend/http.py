# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later


from wazo_dird.auth import required_acl
from wazo_dird.helpers import SourceItem, SourceList

from .schemas import list_schema, source_list_schema, source_schema


class PersonalList(SourceList):
    list_schema = list_schema
    source_schema = source_schema
    source_list_schema = source_list_schema

    @required_acl('dird.backends.personal.sources.read')
    def get(self):
        return super().get()

    @required_acl('dird.backends.personal.sources.create')
    def post(self):
        return super().post()


class PersonalItem(SourceItem):
    source_schema = source_schema

    @required_acl('dird.backends.personal.sources.{source_uuid}.delete')
    def delete(self, source_uuid):
        return super().delete(source_uuid)

    @required_acl('dird.backends.personal.sources.{source_uuid}.read')
    def get(self, source_uuid):
        return super().get(source_uuid)

    @required_acl('dird.backends.personal.sources.{source_uuid}.update')
    def put(self, source_uuid):
        return super().put(source_uuid)
