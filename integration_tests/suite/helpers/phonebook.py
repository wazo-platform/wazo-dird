import uuid
from types import SimpleNamespace
from typing import Protocol

from .base import BaseDirdIntegrationTest
from .constants import MAIN_TENANT, VALID_TOKEN_MAIN_TENANT


class Tenant(Protocol):
    uuid: str
    name: str
    parent_uuid: str


class BasePhonebookTestCase(BaseDirdIntegrationTest):
    asset = 'phonebook_only'

    def setUp(self):
        self.tenants = {}

    @classmethod
    def get_phonebook(cls, phonebook_uuid, token=VALID_TOKEN_MAIN_TENANT, tenant=None):
        url = cls.url('phonebooks', phonebook_uuid)
        return cls.get(url, token=token, tenant=tenant)

    @classmethod
    def list_phonebooks(cls, token=None, tenant=None, **kwargs):
        token = token or VALID_TOKEN_MAIN_TENANT
        url = cls.url('phonebooks')
        return cls.get(url, params=kwargs, token=token, tenant=tenant)

    @classmethod
    def get_phonebook_contact(
        cls, phonebook_uuid, contact_uuid, token=VALID_TOKEN_MAIN_TENANT, tenant=None
    ):
        url = cls.url('phonebooks', phonebook_uuid, 'contacts', contact_uuid)
        return cls.get(url, token=token, tenant=tenant)

    @classmethod
    def list_phonebook_contacts(
        cls, phonebook_uuid, token=VALID_TOKEN_MAIN_TENANT, tenant=None, **kwargs
    ):
        url = cls.url('phonebooks', phonebook_uuid, 'contacts')
        return cls.get(url, params=kwargs, token=token, tenant=tenant)

    @classmethod
    def post_phonebook(cls, phonebook_body, token=VALID_TOKEN_MAIN_TENANT, tenant=None):
        url = cls.url('phonebooks')
        return cls.post(url, json=phonebook_body, token=token, tenant=tenant)

    @classmethod
    def put_phonebook(
        cls, phonebook_uuid, phonebook_body, token=VALID_TOKEN_MAIN_TENANT, tenant=None
    ):
        url = cls.url('phonebooks', phonebook_uuid)
        return cls.put(url, json=phonebook_body, token=token, tenant=tenant)

    @classmethod
    def post_phonebook_contact(
        cls, phonebook_uuid, contact_body, token=VALID_TOKEN_MAIN_TENANT, tenant=None
    ):
        url = cls.url('phonebooks', phonebook_uuid, 'contacts')
        return cls.post(url, json=contact_body, token=token, tenant=tenant)

    @classmethod
    def import_phonebook_contact(
        cls, phonebook_uuid, body, token=VALID_TOKEN_MAIN_TENANT, tenant=None
    ):
        url = cls.url('phonebooks', phonebook_uuid, 'contacts', 'import')
        headers = {'X-Auth-Token': token, 'Context-Type': 'text/csv; charset=utf-8'}
        return cls.post(url, data=body, headers=headers, tenant=tenant)

    @classmethod
    def put_phonebook_contact(
        cls,
        phonebook_uuid,
        contact_uuid,
        contact_body,
        token=VALID_TOKEN_MAIN_TENANT,
        tenant=None,
    ):
        url = cls.url('phonebooks', phonebook_uuid, 'contacts', contact_uuid)
        return cls.put(url, json=contact_body, token=token, tenant=tenant)

    @classmethod
    def delete_phonebook(
        cls, phonebook_uuid, token=VALID_TOKEN_MAIN_TENANT, tenant=None
    ):
        url = cls.url('phonebooks', phonebook_uuid)
        return cls.delete(url, token=token, tenant=tenant)

    @classmethod
    def delete_phonebook_contact(
        cls, phonebook_uuid, contact_uuid, token=VALID_TOKEN_MAIN_TENANT, tenant=None
    ):
        url = cls.url('phonebooks', phonebook_uuid, 'contacts', contact_uuid)
        return cls.delete(url, token=token, tenant=tenant)

    def tearDown(self):
        for tenant in self.tenants.values():
            try:
                phonebooks = self.list_phonebooks(tenant=tenant['uuid']).json()['items']
            except Exception:
                continue

            for phonebook in phonebooks:
                try:
                    self.delete_phonebook(phonebook['uuid'], tenant=tenant['uuid'])
                except Exception:
                    pass

    def _generate_tenant(self, tenant_name):
        return {
            'uuid': str(uuid.uuid4()),
            'name': tenant_name,
            'parent_uuid': MAIN_TENANT,
        }

    def set_tenants(self, *tenant_names: str) -> list[Tenant]:
        items = [{'uuid': MAIN_TENANT}]
        for tenant_name in tenant_names:
            if tenant_name not in self.tenants:
                self.tenants.setdefault(
                    tenant_name,
                    self._generate_tenant(tenant_name),
                )
            items.append(self.tenants[tenant_name])
        self.mock_auth_client.set_tenants(*items)
        return [SimpleNamespace(**item) for item in items[1:]]
