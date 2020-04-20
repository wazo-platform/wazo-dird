# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from graphql import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLField,
    GraphQLList,
    GraphQLString,
)


def make_schema(resolver):
    contact = GraphQLObjectType(
        name='contact',
        fields={
            'firstname': GraphQLField(
                type=GraphQLString, resolver=resolver.get_contact_firstname
            ),
        },
    )

    user = GraphQLObjectType(
        name='user',
        fields={
            'contacts': GraphQLField(
                GraphQLList(type=contact), resolver=resolver.get_user_contacts
            )
        },
    )

    return GraphQLSchema(
        query=GraphQLObjectType(
            name='root_query_type',
            fields={
                'hello': GraphQLField(type=GraphQLString, resolver=resolver.hello),
                'me': GraphQLField(type=user, resolver=resolver.get_user_me),
            },
        )
    )
