# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections.abc import Callable, Iterator, Mapping
from typing import Any

import requests
from wazo_auth_client import Client as Auth

from wazo_dird.plugin_helpers.sorting import sort_contacts

from .exceptions import (
    GoogleTokenNotFoundException,
    GoogleTokenRejectedException,
    GoogleUnavailableException,
)

logger = logging.getLogger(__name__)

DEFAULT_CONTACTS_CACHE_TTL = 300
REQUEST_TIMEOUT = 10

Contacts = list[dict[str, Any]]


def contacts_cache_ttl(main_config: Mapping[str, Any]) -> int:
    google_config = main_config.get('google_backend') or {}
    ttl = google_config.get('contacts_cache_ttl', DEFAULT_CONTACTS_CACHE_TTL)
    # bool is a subclass of int
    if isinstance(ttl, bool) or not isinstance(ttl, int) or ttl < 0:
        logger.warning(
            'Invalid google_backend.contacts_cache_ttl %r, using %d',
            ttl,
            DEFAULT_CONTACTS_CACHE_TTL,
        )
        return DEFAULT_CONTACTS_CACHE_TTL
    return ttl


class _Fetch:
    """A download in progress shared by multiple waiting requests"""

    def __init__(self) -> None:
        self.done = threading.Event()
        self.contacts: Contacts = []
        self.error: Exception | None = None


class ContactsCache:
    """Thread-safe TTL cache of contact lists keyed by Google access token.

    Concurrent misses for the same token share a single download, including
    its failure, instead of each fetching every page from Google. Tokens are
    hashed so they are not kept as dictionary keys.
    """

    MAX_ENTRIES = 1000

    def __init__(self, ttl: int) -> None:
        self.ttl = ttl
        self._lock = threading.Lock()
        self._entries: dict[str, tuple[float, Contacts]] = {}
        self._fetches: dict[str, _Fetch] = {}

    def get_or_fetch(
        self, google_token: str, fetch: Callable[[], Contacts]
    ) -> Contacts:
        key = self._key(google_token)
        with self._lock:
            contacts = self._get(key)
            if contacts is not None:
                logger.debug('Using cached contacts from Google')
                return list(contacts)
            in_progress = self._fetches.get(key)
            is_fetcher = in_progress is None
            if in_progress is None:
                in_progress = self._fetches[key] = _Fetch()

        if is_fetcher:
            self._run(key, in_progress, fetch)
        else:
            in_progress.done.wait()

        # A failure is not cached: the next request downloads again
        if in_progress.error is not None:
            raise in_progress.error
        return list(in_progress.contacts)

    def _run(
        self, key: str, in_progress: _Fetch, fetch: Callable[[], Contacts]
    ) -> None:
        try:
            in_progress.contacts = fetch()
        except Exception as e:
            in_progress.error = e
        finally:
            with self._lock:
                if in_progress.error is None:
                    self._set(key, in_progress.contacts)
                del self._fetches[key]
            in_progress.done.set()

    def _get(self, key: str) -> Contacts | None:
        # Called with self._lock held
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, contacts = entry
        if expires_at <= time.monotonic():
            del self._entries[key]
            return None
        return contacts

    def _set(self, key: str, contacts: Contacts) -> None:
        # Called with self._lock held
        now = time.monotonic()
        self._entries.pop(key, None)
        # Every entry has the same TTL and is inserted last, so the oldest
        # entries are the first to expire
        while self._entries and (
            len(self._entries) >= self.MAX_ENTRIES or self._oldest_expiry() <= now
        ):
            del self._entries[next(iter(self._entries))]
        self._entries[key] = (now + self.ttl, contacts)

    def _oldest_expiry(self) -> float:
        expires_at, _ = next(iter(self._entries.values()))
        return expires_at

    @staticmethod
    def _key(google_token: str) -> str:
        return hashlib.sha256(google_token.encode()).hexdigest()


_shared_caches: dict[int, ContactsCache] = {}
_shared_caches_lock = threading.Lock()


def shared_contacts_cache(main_config: Mapping[str, Any]) -> ContactsCache | None:
    """Return the cache shared by every Google source and the contacts view,
    so all requests made with the same access token reuse one entry.
    Return None when the cache is disabled."""
    ttl = contacts_cache_ttl(main_config)
    if ttl == 0:
        return None
    with _shared_caches_lock:
        return _shared_caches.setdefault(ttl, ContactsCache(ttl))


class GoogleService:
    USER_AGENT = 'wazo_ua/1.0'

    people_url = 'https://people.googleapis.com/v1/people/me/connections'

    person_fields = (
        'names,emailAddresses,phoneNumbers,addresses,organizations,biographies'
    )

    def __init__(self, contacts_cache: ContactsCache | None = None) -> None:
        self.formatter = ContactFormatter()
        self.contacts_cache = contacts_cache

    def get_all_contacts(self, google_token: str) -> Contacts:
        """Raise GoogleUnavailableException when any page cannot be fetched"""
        if self.contacts_cache is None:
            return self._fetch_all(google_token)
        return self.contacts_cache.get_or_fetch(
            google_token, lambda: self._fetch_all(google_token)
        )

    def search(
        self, google_token: str, term: str, searched_columns: list[str]
    ) -> Contacts:
        contacts = self.get_all_contacts(google_token)
        # Filter the cached contact list locally instead of querying Google's
        # search endpoint on every search
        lowered_term = term.lower()
        matching_contacts = [
            c for c in contacts if matches_search(c, lowered_term, searched_columns)
        ]
        logger.debug(
            'Searched %d Google contacts locally for term=%s: %d matched',
            len(contacts),
            term,
            len(matching_contacts),
        )
        return matching_contacts

    def get_contacts(
        self, google_token: str, searched_columns: list[str], **list_params: Any
    ) -> tuple[Contacts, int]:
        term = list_params.get('search')
        if term:
            contacts = self.search(google_token, term, searched_columns)
        else:
            contacts = self.get_all_contacts(google_token)
        total = len(contacts)
        sorted_contacts = sort_contacts(contacts, **list_params)
        paginated_contacts = self._paginate(sorted_contacts, **list_params)
        return paginated_contacts, total

    def _fetch_all(self, google_token: str) -> Contacts:
        headers = self.headers(google_token)
        params: dict[str, Any] = {
            'personFields': self.person_fields,
            'pageSize': 1000,
        }

        # A failed page raises and aborts the whole download: a partial list
        # would hide the missing contacts without any error
        contacts, next_page_token = self._get_contacts_page(headers, params)
        while next_page_token:
            page, next_page_token = self._get_contacts_page(
                headers, {**params, 'pageToken': next_page_token}
            )
            contacts.extend(page)
        return contacts

    def _get_contacts_page(
        self, headers: dict[str, str], params: dict[str, Any]
    ) -> tuple[Contacts, str | None]:
        """Return a page of contacts and the token of the next page, if any"""
        response = self._get_request(self.people_url, headers, params)
        try:
            body = response.json()
        except ValueError as e:
            logger.error('Google returned an invalid body from %s', self.people_url)
            raise GoogleUnavailableException(url=self.people_url) from e
        if not isinstance(body, dict):
            logger.error('Google returned an invalid body from %s', self.people_url)
            raise GoogleUnavailableException(url=self.people_url)
        contacts = [self.formatter.format(c) for c in body.get('connections', [])]
        next_page_token: str | None = body.get('nextPageToken')
        return contacts, next_page_token

    def _get_request(
        self,
        url: str,
        headers: dict[str, str],
        params: dict[str, Any],
    ) -> requests.Response:
        # Requests have verify=False because the integration test mock servers do not have proper SSL
        # Find a way to selectively turn off verification during testing only
        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                verify=False,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as e:
            logger.error('Google request to %s failed: %s', url, e)
            raise GoogleUnavailableException(url=url) from e

        if response.status_code in (401, 403):
            # The user's token expired, was revoked or lacks a scope: not a
            # Google outage, and lookups retry on every keystroke
            logger.debug(
                'Google rejected the access token for %s with status %s',
                url,
                response.status_code,
            )
            raise GoogleTokenRejectedException()

        if response.status_code != 200:
            logger.error(
                'Google request to %s failed with status %s', url, response.status_code
            )
            logger.debug('Raw data: %s', response.text)
            raise GoogleUnavailableException(
                url=url, google_status_code=response.status_code
            )

        logger.debug('Get Request Successful: %s', url)
        # Decoding a page of up to 1000 contacts is wasted when debug is off
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Raw data: %s', response.text)
        return response

    def _paginate(
        self,
        contacts: Contacts,
        limit: int | None = None,
        offset: int | None = None,
        **_: Any,
    ) -> Contacts:
        if limit is None and offset is None:
            return contacts

        if offset:
            end = contacts[offset:]
        else:
            end = contacts

        if limit is None:
            return end

        return end[:limit]

    def headers(self, google_token: str) -> dict[str, str]:
        return {
            'User-Agent': self.USER_AGENT,
            'Authorization': f'Bearer {google_token}',
            'Accept': 'application/json',
            'GData-Version': '3.0',
        }


def column_texts(value: Any) -> Iterator[str]:
    """Yield the strings of a contact column, including those nested in the
    lists and dicts of columns such as emails or numbers_by_label"""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for sub_value in value.values():
            yield from column_texts(sub_value)
    elif isinstance(value, list):
        for sub_value in value:
            yield from column_texts(sub_value)


def matches_search(
    contact: dict[str, Any], lowered_term: str, columns: list[str]
) -> bool:
    """lowered_term is lowered once by the caller, not once per contact"""
    return any(
        lowered_term in text.lower()
        for column in columns
        for text in column_texts(contact.get(column))
    )


def get_google_access_token(
    user_uuid: str, wazo_token: str, **auth_config: Any
) -> str | None:
    try:
        auth = Auth(token=wazo_token, **auth_config)
        access_token: str | None = auth.external.get('google', user_uuid).get(
            'access_token'
        )
        return access_token
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            if 'unknown-external-auth-type' in e.response.text:
                logger.debug('The "google" authentication type has not been configured')
                raise GoogleTokenNotFoundException(user_uuid)
            elif 'unknown-external-auth' in e.response.text:
                logger.debug(
                    'user %s has no "google" authentication configured', user_uuid
                )
                raise GoogleTokenNotFoundException(user_uuid)

        logger.error('Google token could not be fetched from wazo-auth, error: %s', e)
        raise GoogleTokenNotFoundException(user_uuid)
    except requests.exceptions.ConnectionError as e:
        logger.error(
            'Unable to connect auth-client for the given parameters: %s, error: %s.',
            auth_config,
            e,
        )
        raise GoogleTokenNotFoundException(user_uuid)
    except requests.RequestException as e:
        logger.error('Error occurred while connecting to wazo-auth, error: %s', e)


class ContactFormatter:
    chars_to_remove = [' ', '-', '(', ')']

    def format(self, contact: dict[str, Any]) -> dict[str, Any]:
        return {
            'id': self._extract_id(contact),
            'name': self._extract_name(contact),
            'firstname': self._extract_first_name(contact),
            'lastname': self._extract_last_name(contact),
            'numbers_by_label': self._extract_numbers_by_label(contact),
            'numbers': self._extract_numbers(contact),
            'numbers_except_label': self._extract_numbers_except_label(contact),
            'emails': self._extract_emails(contact),
            'organizations': self._extract_organizations(contact),
            'addresses': self._extract_addresses(contact),
            'note': self._extract_note(contact),
        }

    @classmethod
    def _extract_emails(cls, contact: dict[str, Any]) -> list[dict[str, Any]]:
        emails = []
        for email in contact.get('emailAddresses', []):
            address = email.get('value')
            if not address:
                continue
            label_or_type = cls._extract_type(email) or ''
            emails.append({'address': address, 'label': label_or_type})
        return emails

    @classmethod
    def _extract_numbers(cls, contact: dict[str, Any]) -> list[str]:
        numbers_by_label = cls._extract_numbers_by_label(contact)
        numbers = []
        mobile = None

        for type_, number in numbers_by_label.items():
            if type_ == 'mobile':
                mobile = number
            else:
                numbers.append(number)

        if mobile:
            numbers.append(mobile)

        return numbers

    @staticmethod
    def _extract_id(contact: dict[str, Any]) -> str | None:
        names = contact.get('names', [])
        if not names:
            return None
        _id: str = names[0].get('metadata', {}).get('source', {}).get('id', '')
        return _id

    @classmethod
    def _extract_numbers_by_label(cls, contact: dict[str, Any]) -> dict[str, str]:
        numbers = {}
        for number in contact.get('phoneNumbers', []):
            type_ = cls._extract_type(number)
            if not type_:
                continue

            number = number.get('value')
            if not number:
                continue

            for char in cls.chars_to_remove:
                number = number.replace(char, '')

            numbers[type_] = number

        return numbers

    @classmethod
    def _extract_numbers_except_label(
        cls, contact: dict[str, Any]
    ) -> dict[str, list[str]]:
        numbers_by_label = cls._extract_numbers_by_label(contact)
        numbers = {}

        for type_ in (
            'home',
            'work',
            'mobile',
            'other',
            'main',
            'home_fax',
            'work_fax',
            'google_voice',
            'pager',
        ):
            candidates = dict(numbers_by_label)
            candidates.pop(type_, None)
            numbers[type_] = list(candidates.values())

        return numbers

    @classmethod
    def _find_name(cls, contact: dict[str, Any]) -> dict[str, Any]:
        names: list[dict[str, Any]] = contact.get('names', [])
        for name_obj in names:
            return name_obj
        return {}

    @classmethod
    def _extract_name(cls, contact: dict[str, Any]) -> str:
        name_obj = cls._find_name(contact)
        name: str = name_obj.get('displayName', '')
        if not name:
            name = name_obj.get('unstructuredName', '')
        return name

    @classmethod
    def _extract_first_name(cls, contact: dict[str, Any]) -> str:
        first_name: str = cls._find_name(contact).get('givenName', '')
        return first_name

    @classmethod
    def _extract_last_name(cls, contact: dict[str, Any]) -> str:
        last_name: str = cls._find_name(contact).get('familyName', '')
        return last_name

    @classmethod
    def _extract_type(cls, entry: dict[str, Any]) -> str:
        type_: str = entry.get('type', 'other')
        return type_

    @classmethod
    def _extract_organizations(cls, contact: dict[str, Any]) -> list[dict[str, Any]]:
        organizations = []
        organizations_from_contact = contact.get('organizations', [])
        for organization in organizations_from_contact:
            organization_name = organization.get('name', '')
            organization_title = organization.get('title', '')
            organizations.append(
                {'name': organization_name, 'title': organization_title}
            )

        return organizations

    @classmethod
    def _extract_addresses(cls, contact: dict[str, Any]) -> list[dict[str, Any]]:
        addresses = []
        addresses_from_contact = contact.get('addresses', [])
        for address in addresses_from_contact:
            formatted_address = address.get('formattedValue', '')
            label_or_type = cls._extract_type(address) or ''
            addresses.append({'address': formatted_address, 'label': label_or_type})

        return addresses

    @classmethod
    def _extract_note(cls, contact: dict[str, Any]) -> str | None:
        bios = contact.get('biographies', [])
        if bios:
            note: str | None = bios[0].get('value')
            return note
        else:
            return ''
