# Copyright 2020-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import TYPE_CHECKING

from graphene import (
    Connection,
    Field,
    Interface,
    List,
    ObjectType,
    Schema,
    String,
    relay,
)

if TYPE_CHECKING:
    from wazo_dird.plugins.source_result import _SourceResult
    from .resolver import ResolveInfo


class ContactInterface(Interface):
    # These are two words... should be first_name and last_name
    firstname = Field(String)
    lastname = Field(String)
    email = Field(String)
    wazo_reverse = Field(String)
    wazo_source_entry_id = Field(String)
    wazo_source_name = Field(String)
    wazo_backend = Field(String)

    @classmethod
    def resolve_type(
        cls, contact: _SourceResult, info: ResolveInfo
    ) -> type[Contact] | type[WazoContact]:
        return info.context['resolver'].get_contact_type(contact, info)

    def resolve_firstname(contact, info: ResolveInfo):
        return info.context['resolver'].get_contact_field(contact, info)

    def resolve_lastname(contact, info: ResolveInfo):
        return info.context['resolver'].get_contact_field(contact, info)

    def resolve_email(contact, info: ResolveInfo):
        return info.context['resolver'].get_contact_field(contact, info)

    def resolve_wazo_reverse(contact, info: ResolveInfo):
        return info.context['resolver'].get_reverse_field(contact, info)

    def resolve_wazo_source_name(contact, info: ResolveInfo):
        return info.context['resolver'].get_source_name(contact, info)

    def resolve_wazo_backend(contact, info: ResolveInfo):
        return info.context['resolver'].get_backend(contact, info)

    def resolve_wazo_source_entry_id(contact, info: ResolveInfo):
        return info.context['resolver'].get_source_entry_id(contact, info)

    def get_node(self, info, id):
        pass


class Contact(ObjectType):
    class Meta:
        interfaces = (ContactInterface,)


class WazoContact(ObjectType):
    class Meta:
        interfaces = (ContactInterface,)

    user_id = Field(String)
    user_uuid = Field(String)
    endpoint_id = Field(String)
    agent_id = Field(String)

    def resolve_user_id(contact, info: ResolveInfo):
        return info.context['resolver'].get_contact_user_id(contact, info)

    def resolve_user_uuid(contact, info: ResolveInfo):
        return info.context['resolver'].get_contact_user_uuid(contact, info)

    def resolve_endpoint_id(contact, info: ResolveInfo):
        return info.context['resolver'].get_contact_endpoint_id(contact, info)

    def resolve_agent_id(contact, info: ResolveInfo):
        return info.context['resolver'].get_contact_agent_id(contact, info)


class ContactConnection(Connection):
    class Meta:
        node = ContactInterface


class UserMe(ObjectType):
    contacts = relay.ConnectionField(
        ContactConnection,
        extens=List(
            String,
            description='Return only contacts having exactly one of the given extens',
        ),
        profile=String(
            description='Name of the profile defining where contacts are searched',
        ),
    )
    user_uuid = Field(String)

    def resolve_contacts(parent, info, **args):
        return info.context['resolver'].get_user_contacts(parent, info, **args)

    def resolve_user_uuid(parent, info, **args):
        return info.context['resolver'].get_user_me_uuid(parent, info, **args)


class Query(ObjectType):
    hello = Field(String, description='Return "world"')
    me = Field(UserMe, description='The user linked to the authentication token')

    def resolve_hello(root, info: ResolveInfo):
        return info.context['resolver'].hello(root, info)

    def resolve_me(root, info: ResolveInfo):
        return info.context['resolver'].get_user_me(root, info)


def make_schema() -> Schema:
    return Schema(query=Query, types=[WazoContact, Contact])
