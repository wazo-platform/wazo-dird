import uuid

from .base import BaseDirdIntegrationTest
from .constants import MAIN_TENANT, VALID_TOKEN_MAIN_TENANT


class BaseDeprecatedPhonebookTestCase(BaseDirdIntegrationTest):
    asset = 'phonebook_only'

    def setUp(self):
        self.tenants = {}

    @classmethod
    def get_phonebook(cls, tenant, phonebook_id, token=VALID_TOKEN_MAIN_TENANT):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id)
        return cls.get(url, token=token)

    @classmethod
    def list_phonebooks(cls, tenant, token=None, **kwargs):
        token = token or VALID_TOKEN_MAIN_TENANT
        url = cls.url('tenants', tenant, 'phonebooks')
        return cls.get(url, params=kwargs, token=token)

    @classmethod
    def get_phonebook_contact(
        cls, tenant, phonebook_id, contact_uuid, token=VALID_TOKEN_MAIN_TENANT
    ):
        url = cls.url(
            'tenants', tenant, 'phonebooks', phonebook_id, 'contacts', contact_uuid
        )
        return cls.get(url, token=token)

    @classmethod
    def list_phonebook_contacts(
        cls, tenant, phonebook_id, token=VALID_TOKEN_MAIN_TENANT, **kwargs
    ):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id, 'contacts')
        return cls.get(url, params=kwargs, token=token)

    @classmethod
    def post_phonebook(cls, tenant, phonebook_body, token=VALID_TOKEN_MAIN_TENANT):
        url = cls.url('tenants', tenant, 'phonebooks')
        return cls.post(url, json=phonebook_body, token=token)

    @classmethod
    def put_phonebook(
        cls, tenant, phonebook_id, phonebook_body, token=VALID_TOKEN_MAIN_TENANT
    ):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id)
        return cls.put(url, json=phonebook_body, token=token)

    @classmethod
    def post_phonebook_contact(
        cls, tenant, phonebook_id, contact_body, token=VALID_TOKEN_MAIN_TENANT
    ):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id, 'contacts')
        return cls.post(url, json=contact_body, token=token)

    @classmethod
    def import_phonebook_contact(
        cls, tenant, phonebook_id, body, token=VALID_TOKEN_MAIN_TENANT
    ):
        url = cls.url(
            'tenants', tenant, 'phonebooks', phonebook_id, 'contacts', 'import'
        )
        headers = {'X-Auth-Token': token, 'Context-Type': 'text/csv; charset=utf-8'}
        return cls.post(url, data=body, headers=headers)

    @classmethod
    def put_phonebook_contact(
        cls,
        tenant,
        phonebook_id,
        contact_uuid,
        contact_body,
        token=VALID_TOKEN_MAIN_TENANT,
    ):
        url = cls.url(
            'tenants', tenant, 'phonebooks', phonebook_id, 'contacts', contact_uuid
        )
        return cls.put(url, json=contact_body, token=token)

    @classmethod
    def delete_phonebook(cls, tenant, phonebook_id, token=VALID_TOKEN_MAIN_TENANT):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id)
        return cls.delete(url, token=token)

    @classmethod
    def delete_phonebook_contact(
        cls, tenant, phonebook_id, contact_id, token=VALID_TOKEN_MAIN_TENANT
    ):
        url = cls.url(
            'tenants', tenant, 'phonebooks', phonebook_id, 'contacts', contact_id
        )
        return cls.delete(url, token=token)

    def tearDown(self):
        for tenant_name in self.tenants:
            try:
                phonebooks = self.list_phonebooks(tenant_name)['items']
            except Exception:
                continue

            for phonebook in phonebooks:
                try:
                    self.delete_phonebook(tenant_name, phonebook['id'])
                except Exception:
                    pass

    def set_tenants(self, *tenant_names):
        items = [{'uuid': MAIN_TENANT}]
        for tenant_name in tenant_names:
            self.tenants.setdefault(
                tenant_name,
                {
                    'uuid': str(uuid.uuid4()),
                    'name': tenant_name,
                    'parent_uuid': MAIN_TENANT,
                },
            )
            items.append(self.tenants[tenant_name])
        self.mock_auth_client.set_tenants(*items)
