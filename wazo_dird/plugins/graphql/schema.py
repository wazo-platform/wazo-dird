# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from graphql import (
    GraphQLArgument,
    GraphQLField,
    GraphQLList,
    GraphQLObjectType,
    GraphQLSchema,
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

    user_me = GraphQLObjectType(
        name='user_me',
        fields={
            'contacts': GraphQLField(
                GraphQLList(type=contact),
                args={
                    'extens': GraphQLArgument(
                        description='Return only contacts having exactly one of the given extens',
                        type=GraphQLList(type=GraphQLString),
                    ),
                },
                resolver=resolver.get_user_contacts,
            ),
            'user_uuid': GraphQLField(
                GraphQLString, resolver=resolver.get_user_me_uuid,
            ),
        },
    )

    return GraphQLSchema(
        query=GraphQLObjectType(
            name='root_query_type',
            fields={
                'hello': GraphQLField(type=GraphQLString, resolver=resolver.hello),
                'me': GraphQLField(type=user_me, resolver=resolver.get_user_me),
            },
        )
    )
