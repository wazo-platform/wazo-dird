# -*- coding: utf-8 -*-

# Copyright (C) 2016 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import functools
import uuid
import os
import unittest

from hamcrest import (assert_that,
                      any_of,
                      calling,
                      contains,
                      contains_inanyorder,
                      empty,
                      equal_to,
                      not_,
                      raises)
from mock import ANY

from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_

from xivo_dird import database

from .base_dird_integration_test import BaseDirdIntegrationTest

Session = sessionmaker()


def new_uuid():
    return str(uuid.uuid4())


def expected(contact):
    result = {'id': ANY}
    result.update(contact)
    return result


def with_user_uuid(f):
    @functools.wraps(f)
    def wrapped(self, *args, **kwargs):
        user_uuid = new_uuid()
        user = database.User(xivo_user_uuid=user_uuid)
        session = Session()
        session.add(user)
        session.commit()
        result = f(self, user_uuid, *args, **kwargs)
        session.query(database.User).filter(database.User.xivo_user_uuid == user_uuid).delete()
        session.commit()
        return result
    return wrapped


class DBStarter(BaseDirdIntegrationTest):

    asset = 'database'


def setup():
    DBStarter.setUpClass()
    db_uri = os.getenv('DB_URI', 'postgresql://asterisk:proformatique@localhost:15432')
    engine = create_engine(db_uri)
    database.Base.metadata.bind = engine
    database.Base.metadata.reflect()
    database.Base.metadata.drop_all()
    database.Base.metadata.create_all()


def teardown():
    DBStarter.tearDownClass()


class _BaseTest(unittest.TestCase):

    def setUp(self):
        self._contact_1 = {u'firtname': u'Finley',
                           u'lastname': u'Shelley',
                           u'number': u'5555551111'}
        self._contact_2 = {u'firstname': u'Cédric',
                           u'lastname': u'Ora',
                           u'number': u'5555550001'}
        self._contact_3 = {u'firstname': u'Foo',
                           u'lastname': u'Bar',
                           u'number': u'5555550001'}

    @property
    def contact_1(self):
        return dict(self._contact_1)

    @property
    def contact_2(self):
        return dict(self._contact_2)

    @property
    def contact_3(self):
        return dict(self._contact_3)

    def _insert_personal_contacts(self, xivo_user_uuid, *contacts):
        ids = []
        session = Session()
        for contact in contacts:
            hash_ = database.compute_contact_hash(contact)
            dird_contact = database.Contact(user_uuid=xivo_user_uuid, hash=hash_)
            session.add(dird_contact)
            session.flush()
            ids.append(dird_contact.uuid)
            for name, value in contact.iteritems():
                field = database.ContactFields(name=name, value=value, contact_uuid=dird_contact.uuid)
                session.add(field)
        session.commit()
        return ids


class TestContactCRUD(_BaseTest):

    def setUp(self):
        super(TestContactCRUD, self).setUp()
        self._crud = database.PersonalContactCRUD(Session)

    def test_that_create_personal_contact_creates_a_contact_and_the_owner(self):
        owner = new_uuid()

        result = self._crud.create_personal_contact(owner, self.contact_1)
        assert_that(result, equal_to(expected(self.contact_1)))

        contact_list = self._crud.list_personal_contacts(owner)
        assert_that(contact_list, contains(expected(self.contact_1)))

    @with_user_uuid
    def test_that_create_personal_contact_creates_a_contact_with_an_existing_owner(self, xivo_user_uuid):
        result = self._crud.create_personal_contact(xivo_user_uuid, self.contact_1)
        assert_that(result, equal_to(expected(self.contact_1)))

        contact_list = self._crud.list_personal_contacts(xivo_user_uuid)
        assert_that(contact_list, contains(expected(self.contact_1)))

    @with_user_uuid
    def test_that_personal_contacts_are_unique(self, xivo_user_uuid):
        self._crud.create_personal_contact(xivo_user_uuid, self.contact_1)
        assert_that(calling(self._crud.create_personal_contact).with_args(xivo_user_uuid, self.contact_1),
                    raises(database.DuplicatedContactException))

    @with_user_uuid
    def test_that_personal_contacts_remain_unique(self, xivo_user_uuid):
        contact_1_uuid = self._crud.create_personal_contact(xivo_user_uuid, self.contact_1)['id']
        self._crud.create_personal_contact(xivo_user_uuid, self.contact_2)['id']

        assert_that(calling(self._crud.edit_personal_contact).with_args(xivo_user_uuid, contact_1_uuid, self.contact_2),
                    raises(database.DuplicatedContactException))
        contact_list = self._crud.list_personal_contacts(xivo_user_uuid)
        assert_that(contact_list, contains_inanyorder(expected(self.contact_1), expected(self.contact_2)))

    @with_user_uuid
    @with_user_uuid
    def test_that_personal_contacts_can_be_duplicated_between_users(self, user_uuid_1, user_uuid_2):
        contact_1_uuid = self._crud.create_personal_contact(user_uuid_1, self.contact_1)['id']
        contact_2_uuid = self._crud.create_personal_contact(user_uuid_2, self.contact_1)['id']

        assert_that(contact_1_uuid, not_(equal_to(contact_2_uuid)))

    @with_user_uuid
    def test_get_personal_contact(self, xivo_user_uuid):
        contact_uuid, _, __ = self._insert_personal_contacts(xivo_user_uuid,
                                                             self.contact_1,
                                                             self.contact_2,
                                                             self.contact_3)

        result = self._crud.get_personal_contact(xivo_user_uuid, contact_uuid)

        assert_that(result, equal_to(expected(self.contact_1)))

    @with_user_uuid
    @with_user_uuid
    def test_get_personal_contact_from_another_user(self, user_1_uuid, user_2_uuid):
        contact_uuid, _, __ = self._insert_personal_contacts(user_1_uuid, self.contact_1, self.contact_2, self.contact_3)

        assert_that(calling(self._crud.get_personal_contact).with_args(user_2_uuid, contact_uuid),
                    raises(database.NoSuchPersonalContact))

    @with_user_uuid
    def test_delete_personal_contact(self, xivo_user_uuid):
        contact_uuid, = self._insert_personal_contacts(xivo_user_uuid, self.contact_1)

        self._crud.delete_personal_contact(xivo_user_uuid, contact_uuid)

        assert_that(calling(self._crud.get_personal_contact).with_args(xivo_user_uuid, contact_uuid),
                    raises(database.NoSuchPersonalContact))

    @with_user_uuid
    @with_user_uuid
    def test_delete_personal_contact_from_another_user(self, user_1_uuid, user_2_uuid):
        contact_uuid, = self._insert_personal_contacts(user_1_uuid, self.contact_1)

        assert_that(calling(self._crud.delete_personal_contact).with_args(user_2_uuid, contact_uuid),
                    raises(database.NoSuchPersonalContact))

    @with_user_uuid
    @with_user_uuid
    def test_delete_all_personal_contact_from_another_user(self, user_1_uuid, user_2_uuid):
        contact_uuid_1, = self._insert_personal_contacts(user_1_uuid, self.contact_1)
        contact_uuid_2, contact_uuid_3 = self._insert_personal_contacts(user_2_uuid, self.contact_2, self.contact_3)

        self._crud.delete_all_personal_contacts(user_2_uuid)

        assert_that(calling(self._crud.get_personal_contact).with_args(user_1_uuid, contact_uuid_1),
                    not_(raises(database.NoSuchPersonalContact)))
        assert_that(calling(self._crud.get_personal_contact).with_args(user_2_uuid, contact_uuid_2),
                    raises(database.NoSuchPersonalContact))
        assert_that(calling(self._crud.get_personal_contact).with_args(user_2_uuid, contact_uuid_3),
                    raises(database.NoSuchPersonalContact))


class TestFavoriteCrud(_BaseTest):

    def setUp(self):
        super(TestFavoriteCrud, self).setUp()
        self._crud = database.FavoriteCRUD(Session)

    def test_that_create_creates_a_favorite(self):
        xivo_user_uuid = new_uuid()
        source_name = 'foobar'
        contact_id = 'the-contact-id'

        favorite = self._crud.create(xivo_user_uuid, source_name, contact_id)

        assert_that(favorite.user_uuid, equal_to(xivo_user_uuid))
        assert_that(favorite.contact_id, equal_to(contact_id))

        assert_that(self._user_exists(xivo_user_uuid))
        assert_that(self._favorite_exists(xivo_user_uuid, source_name, contact_id))

    @with_user_uuid
    @with_user_uuid
    def test_get(self, user_1, user_2):
        self._crud.create(user_1, 's1', '1')
        self._crud.create(user_1, 's2', '1')
        self._crud.create(user_1, 's1', '42')
        self._crud.create(user_2, 's1', '42')
        self._crud.create(user_2, 's3', '1')

        fav_1 = self._crud.get(user_1)
        fav_2 = self._crud.get(user_2)

        assert_that(fav_1, contains_inanyorder(
            ('s1', '1'),
            ('s2', '1'),
            ('s1', '42'),
        ))
        assert_that(fav_2, contains_inanyorder(
            ('s1', '42'),
            ('s3', '1'),
        ))

    @with_user_uuid
    def test_that_delete_removes_a_favorite(self, xivo_user_uuid):
        self._crud.create(xivo_user_uuid, 'source', 'the-contact-id')

        self._crud.delete(xivo_user_uuid, 'the-contact-id')

        assert_that(self._favorite_exists(xivo_user_uuid, 'source', 'the-contact-id'),
                    equal_to(False))

    @with_user_uuid
    @with_user_uuid
    def test_that_delete_does_not_remove_favorites_from_other_users(self, user_1, user_2):
        self._crud.create(user_2, 'source', 'the-contact-id')

        assert_that(calling(self._crud.delete).with_args(user_1, 'the-contact-id'),
                    raises(database.NoSuchFavorite))

        assert_that(self._favorite_exists(user_2, 'source', 'the-contact-id'))

    @with_user_uuid
    def test_that_delete_raises_if_not_found(self, xivo_user_uuid):
        assert_that(calling(self._crud.delete).with_args(xivo_user_uuid, 'the-contact-id'),
                    raises(database.NoSuchFavorite))

    def _user_exists(self, xivo_user_uuid):
        session = Session()

        user_uuid = session.query(database.User.xivo_user_uuid).filter(
            database.User.xivo_user_uuid == xivo_user_uuid
        ).scalar()

        return user_uuid is not None

    def _favorite_exists(self, xivo_user_uuid, source_name, contact_id):
        session = Session()

        favorite = (session.query(database.Favorite)
                    .join(database.Source)
                    .join(database.User)
                    .filter(and_(database.User.xivo_user_uuid == xivo_user_uuid,
                                 database.Source.name == source_name,
                                 database.Favorite.contact_id == contact_id))).first()

        return favorite is not None


class TestPersonalContactSearchEngine(_BaseTest):

    @with_user_uuid
    def test_that_find_first_returns_a_contact(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, first_match_columns=['number'])

        self._insert_personal_contacts(xivo_user_uuid, self.contact_1, self.contact_2, self.contact_3)

        result = engine.find_first_personal_contact(xivo_user_uuid, u'5555550001')

        assert_that(result, contains(any_of(expected(self.contact_2), expected(self.contact_3))))

    @with_user_uuid
    def test_that_listing_personal_contacts_returns_the_searched_contacts(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=['firstname'])

        ids = self._insert_personal_contacts(xivo_user_uuid, self.contact_1, self.contact_2)

        result = engine.list_personal_contacts(xivo_user_uuid, ids)
        assert_that(result, contains_inanyorder(expected(self.contact_1), expected(self.contact_2)))

        result = engine.list_personal_contacts(xivo_user_uuid, ids[:1])
        assert_that(result, contains(expected(self.contact_1)))

        result = engine.list_personal_contacts(xivo_user_uuid, ids[1:])
        assert_that(result, contains(expected(self.contact_2)))

    @with_user_uuid
    @with_user_uuid
    def test_that_listing_personal_contacts_only_the_users_contact(self, uuid_1, uuid_2):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=['firstname'])

        ids_1 = self._insert_personal_contacts(uuid_1, self.contact_1, self.contact_2)
        ids_2 = self._insert_personal_contacts(uuid_2, self.contact_1, self.contact_3)

        result = engine.list_personal_contacts(uuid_1, ids_1)
        assert_that(result, contains_inanyorder(expected(self.contact_1), expected(self.contact_2)))

        result = engine.list_personal_contacts(uuid_2, ids_2)
        assert_that(result, contains_inanyorder(expected(self.contact_1), expected(self.contact_3)))

        result = engine.list_personal_contacts(uuid_1, ids_2)
        assert_that(result, empty())

        result = engine.list_personal_contacts(uuid_2, ids_1)
        assert_that(result, empty())

    @with_user_uuid
    def test_that_searching_for_a_contact_returns_its_fields(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=['firstname'])

        self._insert_personal_contacts(xivo_user_uuid, self.contact_1, self.contact_2)

        result = engine.find_personal_contacts(xivo_user_uuid, u'ced')
        assert_that(result, contains(expected(self.contact_2)))

        result = engine.find_personal_contacts(xivo_user_uuid, u'céd')
        assert_that(result, contains(expected(self.contact_2)))

    @with_user_uuid
    def test_that_find_searches_only_in_searched_columns(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=['lastname'])

        self._insert_personal_contacts(xivo_user_uuid, self.contact_1, self.contact_2)

        result = engine.find_personal_contacts(xivo_user_uuid, u'ced')

        assert_that(result, empty())

    @with_user_uuid
    def test_that_no_searched_columns_does_not_search(self, xivo_user_uuid):
        engine = database.PersonalContactSearchEngine(Session, searched_columns=[])

        self._insert_personal_contacts(xivo_user_uuid, self.contact_1, self.contact_2)

        result = engine.find_personal_contacts(xivo_user_uuid, u'ced')

        assert_that(result, empty())
