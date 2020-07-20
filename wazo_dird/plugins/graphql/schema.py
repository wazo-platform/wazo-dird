# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from graphene import ObjectType, String, Schema, Field, List, relay, Connection


def make_schema(resolver):
    class Contact(ObjectType):
        class Meta:
            interfaces = [relay.Node]

        firstname = Field(String)
        lastname = Field(String)
        wazo_reverse = Field(String)
        wazo_source_entry_id = Field(String)
        wazo_source_name = Field(String)
        wazo_backend = Field(String)

        def resolve_firstname(contact, info):
            return resolver.get_contact_field(contact, info)

        def resolve_lastname(contact, info):
            return resolver.get_contact_field(contact, info)

        def resolve_wazo_reverse(contact, info):
            return resolver.get_reverse_field(contact, info)

        def resolve_wazo_source_name(contact, info):
            return resolver.get_source_name(contact, info)

        def resolve_wazo_backend(contact, info):
            return resolver.get_backend(contact, info)

        def resolve_wazo_source_entry_id(contact, info):
            return resolver.get_source_entry_id(contact, info)

        def get_node(self, info, id):
            pass

    class ContactConnection(Connection):
        class Meta:
            node = Contact

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
            return resolver.get_user_contacts(parent, info, **args)

        def resolve_user_uuid(parent, info, **args):
            return resolver.get_user_me_uuid(parent, info, **args)

    class Query(ObjectType):
        hello = Field(String, description='Return "world"')
        me = Field(UserMe, description='The user linked to the authentication token')

        def resolve_hello(root, info):
            return resolver.hello(root, info)

        def resolve_me(root, info):
            return resolver.get_user_me(root, info)

    return Schema(query=Query)
