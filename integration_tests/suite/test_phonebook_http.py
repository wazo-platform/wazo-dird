# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from contextlib import ExitStack, contextmanager
from typing import Iterator, TypedDict
from unittest.mock import ANY
from uuid import uuid4

import requests
from hamcrest import (
    all_of,
    assert_that,
    calling,
    contains,
    contains_inanyorder,
    equal_to,
    has_entries,
    has_length,
    has_properties,
    instance_of,
    not_,
    only_contains,
)
from wazo_dird_client import Client as DirdClient
from wazo_test_helpers.hamcrest.raises import raises
from wazo_test_helpers.hamcrest.uuid_ import uuid_

from wazo_dird.database.queries.phonebook import (
    PhonebookContactCRUD,
    PhonebookCRUD,
    PhonebookKey,
)

from .helpers.constants import (
    MAIN_TENANT,
    SUB_TENANT,
    UNKNOWN_UUID,
    VALID_TOKEN_MAIN_TENANT,
    VALID_TOKEN_SUB_TENANT,
)
from .helpers.fixtures import http as fixtures
from .helpers.phonebook import BasePhonebookTestCase

logger = logging.getLogger(__name__)


def generate_phonebook_uuid():
    return str(uuid4())


class PhonebookSource(TypedDict):
    uuid: str
    name: str
    phonebook_uuid: str


class BasePhonebookCRUDTestCase(BasePhonebookTestCase):
    asset = 'all_routes'
    valid_body = {'name': 'main', 'phonebook_uuid': generate_phonebook_uuid()}

    def assert_unknown_source_exception(self, source_uuid, exception):
        assert_that(exception.response.status_code, equal_to(404))
        assert_that(
            exception.response.json(),
            has_entries(
                error_id='unknown-source',
                resource='sources',
                details=has_entries(uuid=source_uuid),
            ),
        )

    @contextmanager
    def source(self, client: DirdClient, *args, **kwargs) -> Iterator[PhonebookSource]:
        try:
            _source = client.phonebook_source.create(*args, **kwargs)
        except requests.HTTPError as ex:
            logger.exception("Error trying to create source: %s", ex.response.content)
            print(ex.response.content)
            raise
        try:
            yield _source
        finally:
            client.phonebook_source.delete(_source['uuid'])


class TestDelete(BasePhonebookCRUDTestCase):
    @fixtures.phonebook_source(name='foobar')
    def test_delete(self, foobar):
        assert_that(
            calling(self.client.phonebook_source.delete).with_args(foobar['uuid']),
            not_(raises(Exception)),
        )

        assert_that(
            calling(self.client.phonebook_source.get).with_args(foobar['uuid']),
            raises(Exception).matching(
                has_properties(response=has_properties(status_code=404))
            ),
        )

        try:
            self.client.phonebook_source.delete(UNKNOWN_UUID)
        except Exception as e:
            self.assert_unknown_source_exception(UNKNOWN_UUID, e)
        else:
            self.fail('Should have raised')

    @fixtures.phonebook_source(name='foomain', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.phonebook_source(name='foosub', token=VALID_TOKEN_SUB_TENANT)
    def test_delete_multi_tenant(self, sub, main):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        try:
            sub_tenant_client.phonebook_source.delete(main['uuid'])
        except Exception as e:
            self.assert_unknown_source_exception(main['uuid'], e)
        else:
            self.fail('Should have raised')

        assert_that(
            calling(main_tenant_client.phonebook_source.delete).with_args(sub['uuid']),
            not_(raises(Exception)),
        )


class TestList(BasePhonebookCRUDTestCase):
    @fixtures.phonebook_source(name='abc')
    @fixtures.phonebook_source(name='bcd')
    @fixtures.phonebook_source(name='cde')
    def test_searches(self, c, b, a):
        assert_that(
            self.client.phonebook_source.list(),
            has_entries(items=contains_inanyorder(a, b, c), total=3, filtered=3),
        )

        assert_that(
            self.client.phonebook_source.list(name='abc'),
            has_entries(items=contains(a), total=3, filtered=1),
        )

        assert_that(
            self.client.phonebook_source.list(uuid=c['uuid']),
            has_entries(items=contains(c), total=3, filtered=1),
        )

        result = self.client.phonebook_source.list(search='b')
        assert_that(
            result, has_entries(items=contains_inanyorder(a, b), total=3, filtered=2)
        )

    @fixtures.phonebook_source(name='abc')
    @fixtures.phonebook_source(name='bcd')
    @fixtures.phonebook_source(name='cde')
    def test_pagination(self, c, b, a):
        assert_that(
            self.client.phonebook_source.list(order='name'),
            has_entries(items=contains(a, b, c), total=3, filtered=3),
        )

        assert_that(
            self.client.phonebook_source.list(order='name', direction='desc'),
            has_entries(items=contains(c, b, a), total=3, filtered=3),
        )

        assert_that(
            self.client.phonebook_source.list(order='name', limit=2),
            has_entries(items=contains(a, b), total=3, filtered=3),
        )

        assert_that(
            self.client.phonebook_source.list(order='name', offset=2),
            has_entries(items=contains(c), total=3, filtered=3),
        )

    @fixtures.phonebook_source(name='abc', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.phonebook_source(name='bcd', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.phonebook_source(name='cde', token=VALID_TOKEN_SUB_TENANT)
    def test_multi_tenant(self, c, b, a):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        assert_that(
            main_tenant_client.phonebook_source.list(),
            has_entries(items=contains_inanyorder(a, b), total=2, filtered=2),
        )

        assert_that(
            main_tenant_client.phonebook_source.list(recurse=True),
            has_entries(items=contains_inanyorder(a, b, c), total=3, filtered=3),
        )

        assert_that(
            sub_tenant_client.phonebook_source.list(),
            has_entries(items=contains_inanyorder(c), total=1, filtered=1),
        )

        assert_that(
            sub_tenant_client.phonebook_source.list(recurse=True),
            has_entries(items=contains_inanyorder(c), total=1, filtered=1),
        )


class TestPost(BasePhonebookCRUDTestCase):
    def test_post(self):
        try:
            self.client.phonebook_source.create({})
        except requests.exceptions.HTTPError as e:
            assert_that(e.response.status_code, equal_to(400))
            assert_that(
                e.response.json(), has_entries(message=ANY, error_id='invalid-data')
            )
        else:
            self.fail('Should have raised')

        with self.source(self.client, self.valid_body):
            assert_that(
                calling(self.client.phonebook_source.create).with_args(self.valid_body),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=409))
                ),
            )

    def test_multi_tenant(self):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        with self.source(main_tenant_client, self.valid_body) as result:
            assert_that(result, has_entries(uuid=uuid_(), tenant_uuid=MAIN_TENANT))

        with self.source(
            main_tenant_client, self.valid_body, tenant_uuid=SUB_TENANT
        ) as result:
            assert_that(result, has_entries(uuid=uuid_(), tenant_uuid=SUB_TENANT))

        with self.source(sub_tenant_client, self.valid_body) as result:
            assert_that(result, has_entries(uuid=uuid_(), tenant_uuid=SUB_TENANT))

        assert_that(
            calling(sub_tenant_client.phonebook_source.create).with_args(
                self.valid_body, tenant_uuid=MAIN_TENANT
            ),
            raises(Exception).matching(
                has_properties(response=has_properties(status_code=401))
            ),
        )

        with self.source(main_tenant_client, self.valid_body):
            assert_that(
                calling(sub_tenant_client.phonebook_source.create).with_args(
                    self.valid_body
                ),
                not_(raises(Exception)),
            )


class TestPut(BasePhonebookCRUDTestCase):
    def setUp(self):
        super().setUp()
        self.new_body = {
            'name': 'new',
            'phonebook_uuid': generate_phonebook_uuid(),
            'searched_columns': ['firstname'],
            'first_matched_columns': ['exten'],
            'format_columns': {'name': '{firstname} {lastname}'},
        }

    @fixtures.phonebook_source(name='foobar')
    @fixtures.phonebook_source(name='other')
    def test_put(self, foobar, other):
        assert_that(
            calling(self.client.phonebook_source.edit).with_args(foobar['uuid'], other),
            raises(Exception).matching(
                has_properties(response=has_properties(status_code=409))
            ),
        )

        assert_that(
            calling(self.client.phonebook_source.edit).with_args(
                UNKNOWN_UUID, self.new_body
            ),
            raises(Exception).matching(
                has_properties(response=has_properties(status_code=404))
            ),
        )

        try:
            self.client.phonebook_source.edit(foobar['uuid'], {})
        except requests.HTTPError as e:
            assert_that(e.response.status_code, equal_to(400))
            assert_that(
                e.response.json(), has_entries(message=ANY, error_id='invalid-data')
            )
        else:
            self.fail('Should have raised')

        assert_that(
            calling(self.client.phonebook_source.edit).with_args(
                foobar['uuid'], self.new_body
            ),
            not_(raises(Exception)),
        )

        result = self.client.phonebook_source.get(foobar['uuid'])
        assert_that(
            result,
            has_entries(
                uuid=foobar['uuid'],
                tenant_uuid=foobar['tenant_uuid'],
                name='new',
                searched_columns=['firstname'],
                first_matched_columns=['exten'],
                format_columns={'name': '{firstname} {lastname}'},
            ),
        )

    @fixtures.phonebook_source(name='foomain', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.phonebook_source(name='foosub', token=VALID_TOKEN_SUB_TENANT)
    def test_put_multi_tenant(self, sub, main):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        assert_that(
            calling(sub_tenant_client.phonebook_source.edit).with_args(
                main['uuid'], sub
            ),
            not_(
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=409))
                )
            ),
        )

        try:
            sub_tenant_client.phonebook_source.edit(main['uuid'], self.new_body)
        except Exception as e:
            self.assert_unknown_source_exception(main['uuid'], e)
        else:
            self.fail('Should have raised')

        assert_that(
            calling(main_tenant_client.phonebook_source.edit).with_args(
                sub['uuid'], self.new_body
            ),
            not_(raises(Exception)),
        )


class TestGet(BasePhonebookCRUDTestCase):
    @fixtures.phonebook_source(name='foobar')
    def test_get(self, wazo):
        response = self.client.phonebook_source.get(wazo['uuid'])
        assert_that(response, equal_to(wazo))

        try:
            self.client.phonebook_source.get(UNKNOWN_UUID)
        except Exception as e:
            self.assert_unknown_source_exception(UNKNOWN_UUID, e)
        else:
            self.fail('Should have raised')

    @fixtures.phonebook_source(name='foomain', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.phonebook_source(name='foosub', token=VALID_TOKEN_SUB_TENANT)
    def test_get_multi_tenant(self, sub, main):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        response = main_tenant_client.phonebook_source.get(sub['uuid'])
        assert_that(response, equal_to(sub))

        try:
            sub_tenant_client.phonebook_source.get(main['uuid'])
        except Exception as e:
            self.assert_unknown_source_exception(main['uuid'], e)
        else:
            self.fail('Should have raised')


class TestGetContacts(BasePhonebookCRUDTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.phonebook_crud = PhonebookCRUD(cls.Session)
        cls.contact_crud = PhonebookContactCRUD(cls.Session)
        cls.stack = ExitStack()

        cls.phonebook = cls.phonebook_crud.create(
            MAIN_TENANT,
            {'name': 'test-phonebook', 'description': 'some test phonebook'},
        )
        cls.stack.callback(
            cls.phonebook_crud.delete, None, PhonebookKey(uuid=cls.phonebook['uuid'])
        )
        cls.contacts, errors = cls.contact_crud.create_many(
            [MAIN_TENANT],
            PhonebookKey(uuid=cls.phonebook['uuid']),
            [
                {
                    'firstname': f'Contact {i}',
                    'lastname': 'McContact',
                    'number': str(1000000000 + i),
                }
                for i in range(5000)
            ],
        )
        assert not errors

    @classmethod
    def tearDownClass(self):
        self.stack.close()
        super().tearDownClass()

    def test_get_all(self):
        client = self.get_client(VALID_TOKEN_MAIN_TENANT)

        with self.source(
            client,
            {
                'phonebook_uuid': self.phonebook['uuid'],
                'name': self.phonebook['name'] + "-source",
            },
        ) as source:
            response = client.session().get(
                url=f"{client.phonebook_source.base_url}/{source['uuid']}/contacts"
            )
            response.raise_for_status()
            body = response.json()
            assert_that(
                body,
                has_entries(
                    total=len(self.contacts),
                    filtered=len(self.contacts),
                    items=all_of(
                        has_length(len(self.contacts)),
                        only_contains(
                            has_entries(
                                firstname=instance_of(str),
                                lastname=instance_of(str),
                                number=instance_of(str),
                                id=instance_of(str),
                            )
                        ),
                    ),
                ),
            )

    def test_get_paginated(self):
        client = self.get_client(VALID_TOKEN_MAIN_TENANT)

        with self.source(
            client,
            {
                'phonebook_uuid': self.phonebook['uuid'],
                'name': self.phonebook['name'] + "-source",
            },
        ) as source:
            limit = 100
            contact_ids: set[str] = set()
            for i in range(5000 // 100):
                logger.debug("request %d", i)
                response = client.session().get(
                    url=f"{client.phonebook_source.base_url}/{source['uuid']}/contacts",
                    params={'limit': 100, 'offset': i * limit},
                )
                response.raise_for_status()
                body = response.json()
                assert_that(
                    body,
                    has_entries(
                        total=len(self.contacts),
                        filtered=len(self.contacts),
                        items=all_of(
                            has_length(100),
                            only_contains(
                                has_entries(
                                    firstname=instance_of(str),
                                    lastname=instance_of(str),
                                    number=instance_of(str),
                                    id=instance_of(str),
                                )
                            ),
                        ),
                    ),
                )
                contact_ids.update(contact['id'] for contact in body['items'])

            assert_that(
                contact_ids, equal_to(set(contact['id'] for contact in self.contacts))
            )

    def test_get_filtered(self):
        client = self.get_client(VALID_TOKEN_MAIN_TENANT)

        with self.source(
            client,
            {
                'phonebook_uuid': self.phonebook['uuid'],
                'name': self.phonebook['name'] + "-source",
            },
        ) as source:
            response = client.session().get(
                url=f"{client.phonebook_source.base_url}/{source['uuid']}/contacts",
                params={'search': 'Contact 4'},
            )
            response.raise_for_status()
            body = response.json()
            assert_that(
                body,
                has_entries(
                    total=len(self.contacts),
                    filtered=1111,
                    items=all_of(
                        has_length(1111),
                        only_contains(
                            has_entries(
                                firstname=instance_of(str),
                                lastname=instance_of(str),
                                number=instance_of(str),
                                id=instance_of(str),
                            )
                        ),
                    ),
                ),
            )
            contact_ids = set(contact['id'] for contact in body['items'])

            assert_that(
                contact_ids,
                equal_to(
                    set(
                        contact['id']
                        for contact in self.contacts
                        if 'Contact 4' in contact.get('firstname', '')
                    )
                ),
            )
