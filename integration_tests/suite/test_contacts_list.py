# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import time

import ldap
import requests
from hamcrest import (
    assert_that,
    contains_exactly,
    contains_inanyorder,
    empty,
    equal_to,
    has_entries,
    has_item,
    has_items,
    has_length,
    is_not,
    less_than,
)
from ldap.modlist import addModlist
from wazo_test_helpers import until
from wazo_test_helpers.auth import MockUserToken

from wazo_dird import database

from .helpers.base import BaseDirdIntegrationTest
from .helpers.config import Config
from .helpers.constants import (
    MAIN_TENANT,
    MAIN_USER_UUID,
    SUB_TENANT,
    VALID_TOKEN_MAIN_TENANT,
    VALID_TOKEN_SUB_TENANT,
    WAZO_UUID,
)

WS = 'http://ws.contacts.test:9485'
USER_B_TOKEN = 'contacts-list-user-b-token'
USER_B_UUID = '00000000-0000-4000-8000-000000000b0b'
NO_USER_TOKEN = 'contacts-list-no-user-token'
LDAP_BASE_DN = 'dc=wazo-dird,dc=wazo,dc=community'
DISPLAY = {'name': 'display', 'columns': [{'title': 'Firstname', 'field': 'firstname'}]}


def _ws_source(config, name, list_name=None, **extra):
    config.with_source(
        backend='csv_ws',
        name=name,
        lookup_url=f'{WS}/list/{list_name or name}',
        list_url=f'{WS}/list/{list_name or name}',
        unique_column='id',
        **extra,
    )


class _ContactsListTest(BaseDirdIntegrationTest):
    asset = 'contacts_list'

    @classmethod
    def list_contacts_result(cls, token=VALID_TOKEN_MAIN_TENANT, tenant=None, **params):
        return cls.get(
            cls.url('directories', 'contacts'),
            params=params,
            token=token,
            tenant=tenant,
        )

    @classmethod
    def list_contacts(cls, token=VALID_TOKEN_MAIN_TENANT, **params):
        response = cls.list_contacts_result(token=token, **params)
        assert_that(response.status_code, equal_to(200), response.text)
        return response.json()

    @classmethod
    def ws_url(cls, *parts):
        return f'http://127.0.0.1:{cls.service_port(9485, "ws")}/{"/".join(parts)}'

    @classmethod
    def ws_set(cls, name, **settings):
        requests.post(cls.ws_url('_set', name), json=settings).raise_for_status()

    @classmethod
    def ws_calls(cls, name):
        return requests.get(cls.ws_url('_calls', name)).json()

    @staticmethod
    def names(page):
        return [(item['source'], item['fields']['firstname']) for item in page['items']]


def new_tenant_config(Session):
    phonebooks = database.PhonebookCRUD(Session)
    phonebook_contacts = database.PhonebookContactCRUD(Session)
    phonebook = phonebooks.create(MAIN_TENANT, {'name': 'shared_phonebook'})
    key = database.PhonebookKey(uuid=phonebook['uuid'])
    for firstname in ('Paula', 'Peter', 'Pierre'):
        phonebook_contacts.create([MAIN_TENANT], key, {'firstname': firstname})

    config = Config(Session)
    config.with_display(**DISPLAY)
    config.with_display(**{**DISPLAY, 'name': 'sub_display', 'tenant_uuid': SUB_TENANT})
    config.with_source(
        backend='phonebook', name='shared_phonebook', phonebook_uuid=phonebook['uuid']
    )
    config.with_source(
        backend='csv',
        name='reverse_only',
        file='/tmp/data/reverse.csv',
        separator=',',
        unique_column='id',
    )
    _ws_source(config, 'favorites_only')
    config.with_source(backend='personal', name='personal')
    config.with_source(
        backend='csv',
        name='sub_tenant_csv',
        tenant_uuid=SUB_TENANT,
        file='/tmp/data/sub.csv',
        separator=',',
        unique_column='id',
    )
    config.with_profile(
        name='first',
        display='display',
        services={'lookup': {'sources': ['shared_phonebook', 'personal']}},
    )
    config.with_profile(
        name='second',
        display='display',
        services={
            'lookup': {'sources': ['shared_phonebook']},
            'reverse': {'sources': ['reverse_only']},
            'favorites': {'sources': ['favorites_only']},
        },
    )
    config.with_profile(
        name='sub',
        tenant_uuid=SUB_TENANT,
        display='sub_display',
        services={'lookup': {'sources': ['sub_tenant_csv']}},
    )
    return config


class TestContactsListOfATenant(_ContactsListTest):
    config_factory = new_tenant_config

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mock_auth_client.set_token(
            MockUserToken(
                USER_B_TOKEN,
                USER_B_UUID,
                WAZO_UUID,
                {'tenant_uuid': MAIN_TENANT, 'uuid': USER_B_UUID},
            )
        )
        cls.mock_auth_client.set_token(
            MockUserToken(
                NO_USER_TOKEN,
                'no-user',
                WAZO_UUID,
                {'tenant_uuid': MAIN_TENANT, 'uuid': None},
            )
        )

    def test_every_source_of_every_profile_is_listed_once(self):
        page = self.list_contacts()

        assert_that(
            self.names(page),
            contains_inanyorder(
                ('favorites_only', 'favorites_only'),
                ('favorites_only', 'favorites_only'),
                ('reverse_only', 'Rachel'),
                ('reverse_only', 'Robert'),
                ('shared_phonebook', 'Paula'),
                ('shared_phonebook', 'Peter'),
                ('shared_phonebook', 'Pierre'),
            ),
        )
        assert_that(page, has_entries(total=7, missing_sources=[]))

    def test_an_item_carries_its_whole_shape(self):
        page = self.list_contacts()

        assert_that(
            page['items'],
            has_item(
                has_entries(
                    source='reverse_only',
                    backend='csv',
                    fields=has_entries(id='1', firstname='Rachel'),
                    relations=has_entries(source_entry_id='1', user_uuid=None),
                    favorite=False,
                    personal=False,
                )
            ),
        )

    def test_the_order_is_by_source_then_id_and_stable(self):
        first, second = self.list_contacts(), self.list_contacts()

        assert_that(first['items'], equal_to(second['items']))
        keys = [
            (item['source'], item['relations']['source_entry_id'])
            for item in first['items']
        ]
        assert_that(keys, equal_to(sorted(keys)))

    def test_a_tenant_the_token_cannot_see_is_refused(self):
        response = self.list_contacts_result(
            token=VALID_TOKEN_SUB_TENANT, tenant=MAIN_TENANT
        )

        assert_that(response.status_code, equal_to(401))
        assert_that(response.json(), is_not(has_item('items')))

    def test_a_visible_sub_tenant_does_not_move_the_scope(self):
        response = self.list_contacts_result(tenant=SUB_TENANT)

        assert_that(response.status_code, equal_to(200))
        sources = {item['source'] for item in response.json()['items']}
        assert_that(
            sources, equal_to({'shared_phonebook', 'reverse_only', 'favorites_only'})
        )

    def test_another_tenants_sources_are_never_listed(self):
        main = self.list_contacts()
        sub = self.list_contacts(token=VALID_TOKEN_SUB_TENANT)

        assert_that(
            {item['source'] for item in main['items']},
            is_not(has_item('sub_tenant_csv')),
        )
        assert_that(self.names(sub), contains_exactly(('sub_tenant_csv', 'Sam')))

    def test_a_user_lists_their_personal_contacts_and_favorites_only(self):
        contact = self.post_personal({'firstname': 'Alice'})
        self.addCleanup(self.delete_personal, contact['id'])
        self.put_favorite('reverse_only', '1')
        self.addCleanup(self.delete_favorite, 'reverse_only', '1')

        mine = self.list_contacts()
        theirs = self.list_contacts(token=USER_B_TOKEN)
        nobody = self.list_contacts(token=NO_USER_TOKEN)

        assert_that(
            mine['items'],
            has_items(
                has_entries(
                    source='personal',
                    personal=True,
                    fields=has_entries(firstname='Alice'),
                ),
                has_entries(
                    source='reverse_only', fields=has_entries(id='1'), favorite=True
                ),
            ),
        )
        for page in (theirs, nobody):
            assert_that(
                [item['source'] for item in page['items']], is_not(has_item('personal'))
            )
            assert_that(
                [item['favorite'] for item in page['items']], is_not(has_item(True))
            )
            assert_that(page['total'], equal_to(7))
        assert_that(mine['total'], equal_to(8))
        assert_that(contact['id'], is_not(equal_to(MAIN_USER_UUID)))


def new_failing_sources_config(Session):
    config = Config(Session)
    config.with_display(**DISPLAY)
    _ws_source(config, 'one_second')
    _ws_source(config, 'too_slow')
    _ws_source(config, 'broken')
    _ws_source(config, 'counted')
    _ws_source(config, 'never_listed')
    config.with_source(
        backend='csv',
        name='missing_file',
        file='/tmp/data/no-such-file.csv',
        separator=',',
        unique_column='id',
    )
    config.with_profile(
        name='default',
        display='display',
        services={
            'reverse': {
                'sources': ['one_second', 'too_slow', 'broken', 'missing_file'],
                'options': {'timeout': 0.5},
            },
            'lookup': {'sources': ['counted']},
        },
    )
    return config


class TestContactsListSources(_ContactsListTest):
    config_factory = new_failing_sources_config

    def setUp(self):
        super().setUp()
        for name in ('one_second', 'too_slow', 'broken', 'counted'):
            self.ws_set(name, delay=0, status=200, size=2)
        self.ws_set('one_second', delay=1)
        self.ws_set('too_slow', delay=4)
        self.ws_set('broken', status=500)
        # the asset keeps a list 3 seconds
        time.sleep(3)

    def test_failing_and_slow_sources_are_missing_and_the_others_listed(self):
        started = time.monotonic()
        page = self.list_contacts()

        assert_that(time.monotonic() - started, less_than(3))
        assert_that(
            {item['source'] for item in page['items']},
            equal_to({'one_second', 'counted'}),
        )
        assert_that(
            page['missing_sources'],
            contains_exactly('broken', 'missing_file', 'too_slow'),
        )
        assert_that(page['total'], equal_to(4))

    def test_a_shared_list_is_asked_once_within_the_delay_then_again(self):
        before = self.ws_calls('counted')

        self.list_contacts()
        self.list_contacts()
        assert_that(self.ws_calls('counted') - before, equal_to(1))
        time.sleep(3)
        self.list_contacts()

        assert_that(self.ws_calls('counted') - before, equal_to(2))

    def test_a_list_above_the_bound_is_asked_every_time(self):
        self.ws_set('counted', size=301)
        before = self.ws_calls('counted')

        first = self.list_contacts()
        self.list_contacts()

        assert_that(self.ws_calls('counted') - before, equal_to(2))
        assert_that(first['total'], equal_to(2 + 301))

    def test_a_failure_is_not_cached(self):
        self.ws_set('counted', status=503)
        before = self.ws_calls('counted')
        failed = self.list_contacts()
        self.ws_set('counted', status=200)

        listed = self.list_contacts()

        assert_that(failed['missing_sources'], has_item('counted'))
        assert_that(listed['missing_sources'], is_not(has_item('counted')))
        assert_that(self.ws_calls('counted') - before, equal_to(2))

    def test_a_source_edit_forgets_its_list(self):
        source = self.config.created_sources['counted']
        before = self.ws_calls('counted')
        self.list_contacts()

        self._edit('counted')
        self.list_contacts()

        assert_that(self.ws_calls('counted') - before, equal_to(2))
        assert_that(source['uuid'], is_not(equal_to(None)))

    def test_editing_a_source_never_listed_succeeds(self):
        response = self._edit('never_listed')

        # the source edit route answers 204
        assert_that(response.status_code, equal_to(204), response.text)

    def _edit(self, name):
        source = self.config.created_sources[name]
        body = {
            'name': name,
            'lookup_url': f'{WS}/list/{name}',
            'list_url': f'{WS}/list/{name}',
            'unique_column': 'id',
            'searched_columns': [],
            'first_matched_columns': [],
            'format_columns': {},
        }
        return self.put(
            self.url('backends', 'csv_ws', 'sources', source['uuid']),
            json=body,
            token=VALID_TOKEN_MAIN_TENANT,
        )


def new_pages_config(Session):
    config = Config(Session)
    config.with_display(**DISPLAY)
    _ws_source(config, 'two_hundred')
    _ws_source(config, 'fifty')
    config.with_profile(
        name='default',
        display='display',
        services={'lookup': {'sources': ['two_hundred', 'fifty']}},
    )
    return config


class TestContactsListPages(_ContactsListTest):
    config_factory = new_pages_config

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ws_set('two_hundred', size=200, delay=0, status=200)
        cls.ws_set('fifty', size=50, delay=0, status=200)

    def test_pages_of_250_contacts(self):
        self._assert_pages_of_250()

    def test_pages_of_250_contacts_without_the_cache(self):
        with self.dird_with_config({'contacts_list': {'cache_ttl': 0}}):
            until.true(self._dird_answers, timeout=30)
            self._assert_pages_of_250()

    def test_without_a_limit_a_page_holds_100(self):
        page = self.list_contacts()

        assert_that(page['items'], has_length(100))

    def test_invalid_bounds_are_refused(self):
        for params in (
            {'limit': 1001},
            {'limit': -1},
            {'limit': 0},
            {'offset': -1},
            {'limit': 'a'},
            {'offset': 'a'},
        ):
            response = self.list_contacts_result(**params)

            assert_that(response.status_code, equal_to(400), str(params))

    def _assert_pages_of_250(self):
        pages = [
            self.list_contacts(limit=100, offset=offset)
            for offset in (0, 100, 200, 300)
        ]

        assert_that([len(p['items']) for p in pages], equal_to([100, 100, 50, 0]))
        assert_that({p['total'] for p in pages}, equal_to({250}))
        ids = [item['fields']['id'] for page in pages for item in page['items']]
        assert_that(ids, has_length(250))
        assert_that(set(ids), has_length(250))
        assert_that(pages[0], equal_to(self.list_contacts(limit=100, offset=0)))

    def _dird_answers(self):
        try:
            return self.list_contacts_result().status_code == 200
        except requests.RequestException:
            return False


def new_ldap_config(Session):
    config = Config(Session)
    config.with_display(**DISPLAY)
    for name, extra in (
        ('ldap_filtered', {'ldap_custom_filter': '(sn=Kept)'}),
        # anonymous: the server's size limit does not apply to its admin
        ('ldap_anonymous', {}),
    ):
        username = (
            {}
            if name == 'ldap_anonymous'
            else {
                'ldap_username': f'cn=admin,{LDAP_BASE_DN}',
                'ldap_password': 'wazopassword',
            }
        )
        config.with_source(
            backend='ldap',
            name=name,
            ldap_uri='ldap://slapd',
            ldap_base_dn=f'ou=people,{LDAP_BASE_DN}',
            unique_column='entryUUID',
            searched_columns=['cn'],
            **username,
            **extra,
        )
    config.with_profile(
        name='ldap',
        display='display',
        services={'lookup': {'sources': ['ldap_filtered', 'ldap_anonymous']}},
    )
    return config


class TestContactsListLDAP(_ContactsListTest):
    config_factory = new_ldap_config
    FRONTEND = '/etc/ldap/slapd.d/cn=config/olcDatabase={-1}frontend.ldif'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            cls._add_people()
        except Exception:
            super().tearDownClass()
            raise

    @classmethod
    def _add_people(cls):
        ldap_obj = cls._ldap_admin()
        ldap_obj.add_s(
            f'ou=people,{LDAP_BASE_DN}',
            addModlist({'objectClass': [b'organizationalUnit'], 'ou': [b'people']}),
        )
        for cn, sn in (
            ('a', 'Kept'),
            ('b', 'Kept'),
            ('c', 'Kept'),
            ('d', 'Kept'),
            ('e', 'Filtered'),
        ):
            ldap_obj.add_s(
                f'cn={cn},ou=people,{LDAP_BASE_DN}',
                addModlist(
                    {
                        'objectClass': [b'inetOrgPerson'],
                        'cn': [cn.encode()],
                        'sn': [sn.encode()],
                    }
                ),
            )

    @classmethod
    def _ldap_admin(cls):
        uri = f'ldap://127.0.0.1:{cls.service_port(389, "slapd")}'
        for _ in range(20):
            try:
                ldap_obj = ldap.initialize(uri)
                ldap_obj.simple_bind_s(f'cn=admin,{LDAP_BASE_DN}', 'wazopassword')
                return ldap_obj
            except ldap.SERVER_DOWN:
                time.sleep(1)
        raise Exception('LDAP server is down')

    @classmethod
    def _set_size_limit(cls, limit):
        cls.docker_exec(
            ['sed', '-i', f's/^olcSizeLimit: .*/olcSizeLimit: {limit}/', cls.FRONTEND],
            service_name='slapd',
        )
        cls.restart_service('slapd')
        cls._ldap_admin()

    def _listed_cns(self, page, source):
        return sorted(
            item['fields'].get('cn')
            for item in page['items']
            if item['source'] == source and 'cn' in item['fields']
        )

    def test_every_entry_under_the_base_dn_is_listed_whatever_the_filter(self):
        page = self.list_contacts()

        assert_that(
            self._listed_cns(page, 'ldap_filtered'),
            equal_to(['a', 'b', 'c', 'd', 'e']),
        )
        assert_that(page['missing_sources'], empty())

    def test_a_directory_above_the_size_limit_is_listed_whole(self):
        # paging reads past the limit when the server allows paged totals
        # beyond it, as Active Directory does
        self._set_size_limit('size.soft=2 size.hard=2 size.prtotal=unlimited')
        self.addCleanup(self._set_size_limit, '500')
        anonymous = ldap.initialize(
            f'ldap://127.0.0.1:{self.service_port(389, "slapd")}'
        )
        anonymous.simple_bind_s('', '')
        self.assertRaises(
            ldap.SIZELIMIT_EXCEEDED,
            anonymous.search_ext_s,
            f'ou=people,{LDAP_BASE_DN}',
            ldap.SCOPE_SUBTREE,
            '(objectClass=*)',
        )
        # the asset keeps a list 3 seconds
        time.sleep(3)

        page = self.list_contacts()

        assert_that(
            self._listed_cns(page, 'ldap_anonymous'),
            equal_to(['a', 'b', 'c', 'd', 'e']),
        )
        assert_that(page['missing_sources'], empty())
