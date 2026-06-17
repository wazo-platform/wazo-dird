# Copyright 2020-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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


class ContactInterface(Interface):  # type: ignore[misc]
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

    def resolve_firstname(contact: _SourceResult, info: ResolveInfo) -> Any:
        return info.context['resolver'].get_contact_field(contact, info)

    def resolve_lastname(contact: _SourceResult, info: ResolveInfo) -> Any:
        return info.context['resolver'].get_contact_field(contact, info)

    def resolve_email(contact: _SourceResult, info: ResolveInfo) -> Any:
        return info.context['resolver'].get_contact_field(contact, info)

    def resolve_wazo_reverse(contact: _SourceResult, info: ResolveInfo) -> Any:
        return info.context['resolver'].get_reverse_field(contact, info)

    def resolve_wazo_source_name(contact: _SourceResult, info: ResolveInfo) -> Any:
        return info.context['resolver'].get_source_name(contact, info)

    def resolve_wazo_backend(contact: _SourceResult, info: ResolveInfo) -> Any:
        return info.context['resolver'].get_backend(contact, info)

    def resolve_wazo_source_entry_id(contact: _SourceResult, info: ResolveInfo) -> Any:
        return info.context['resolver'].get_source_entry_id(contact, info)

    def get_node(self, info: ResolveInfo, id: str) -> None:
        pass


class Contact(ObjectType):  # type: ignore[misc]
    class Meta:
        interfaces = (ContactInterface,)


class WazoContact(ObjectType):  # type: ignore[misc]
    class Meta:
        interfaces = (ContactInterface,)

    user_id = Field(String)
    user_uuid = Field(String)
    endpoint_id = Field(String)
    agent_id = Field(String)

    def resolve_user_id(contact: _SourceResult, info: ResolveInfo) -> Any:
        return info.context['resolver'].get_contact_related_field(contact, info)

    def resolve_user_uuid(contact: _SourceResult, info: ResolveInfo) -> Any:
        return info.context['resolver'].get_contact_user_uuid(contact, info)

    def resolve_endpoint_id(contact: _SourceResult, info: ResolveInfo) -> Any:
        return info.context['resolver'].get_contact_related_field(contact, info)

    def resolve_agent_id(contact: _SourceResult, info: ResolveInfo) -> Any:
        return info.context['resolver'].get_contact_related_field(contact, info)


class ContactConnection(Connection):  # type: ignore[misc]
    class Meta:
        node = ContactInterface


class UserMe(ObjectType):  # type: ignore[misc]
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

    def resolve_contacts(
        parent: _SourceResult, info: ResolveInfo, **args: Any
    ) -> list[Any]:
        return info.context['resolver'].get_user_contacts(parent, info, **args)

    def resolve_user_uuid(parent: _SourceResult, info: ResolveInfo, **args: Any) -> str:
        return info.context['resolver'].get_user_me_uuid(parent, info, **args)


class User(ObjectType):  # type: ignore[misc]
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
    uuid = Field(String)

    def resolve_contacts(
        parent: _SourceResult, info: ResolveInfo, **args: Any
    ) -> list[Any]:
        return info.context['resolver'].get_user_contacts(parent, info, **args)

    def resolve_uuid(parent: _SourceResult, info: ResolveInfo, **args: Any) -> str:
        return info.context['resolver'].get_user_me_uuid(parent, info, **args)


class Query(ObjectType):  # type: ignore[misc]
    hello = Field(String, description='Return "world"')
    me = Field(UserMe, description='The user linked to the authentication token')
    user = Field(User, uuid=String(), description='The user to use for this query')

    def resolve_hello(root: _SourceResult, info: ResolveInfo) -> str:
        return info.context['resolver'].hello(root, info)

    def resolve_me(root: _SourceResult, info: ResolveInfo) -> dict[str, Any]:
        return info.context['resolver'].get_user_me(root, info)

    def resolve_user(root: _SourceResult, info: ResolveInfo, uuid: str) -> Any:
        return info.context['resolver'].get_user_by_uuid(root, info, uuid)


def make_schema() -> Schema:
    return Schema(query=Query, types=[WazoContact, Contact])
