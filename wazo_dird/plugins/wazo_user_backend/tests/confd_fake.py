# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import threading
import unicodedata
from typing import Any


def make_user(
    user_id: int, firstname: str, lastname: str | None, exten: str
) -> dict[str, Any]:
    return {
        'id': user_id,
        'uuid': f'00000000-0000-0000-0000-{user_id:012d}',
        'agent_id': None,
        'line_id': 100 + user_id,
        'firstname': firstname,
        'lastname': lastname,
        'exten': exten,
        'email': None,
        'mobile_phone_number': None,
        'voicemail_number': None,
        'userfield': None,
        'description': None,
    }


# the one request that loads the snapshot
LOAD_PARAMS = {'view': 'directory', 'recurse': True}


class FakeConfd:
    """GET /users like confd: filters, SQL order by lastname, then a collated sort.

    `snapshot_failure` and `gate` act on the load of the snapshot only; `failure`
    acts on every request.
    """

    def __init__(self, users: list[dict[str, Any]]) -> None:
        self.users = list(users)
        self.calls: list[dict[str, Any]] = []
        self.failure: Exception | None = None
        self.snapshot_failure: Exception | None = None
        self.gate: threading.Event | None = None

    def infos(self) -> dict[str, str]:
        return {'uuid': 'my-xivo-uuid'}

    def users_list(self, **params: Any) -> dict[str, Any]:
        self.calls.append(params)
        loading = params == LOAD_PARAMS
        if loading and self.gate is not None:
            assert self.gate.wait(10)
        if self.failure is not None:
            raise self.failure
        if loading and self.snapshot_failure is not None:
            raise self.snapshot_failure

        rows = list(self.users)
        if params.get('search'):
            needle = params['search'].lower()
            rows = [
                u
                for u in rows
                if needle
                in f"{u['firstname']} {u['lastname'] or ''} {u['exten']}".lower()
            ]
        if isinstance(params.get('uuid'), str):
            wanted = params['uuid'].split(',')
            rows = [u for u in rows if u['uuid'] in wanted]
        for column in ('firstname', 'lastname'):
            if params.get(column):
                rows = [u for u in rows if u[column] == params[column]]

        rows.sort(key=lambda user: (user['lastname'] or '').lower())
        order = params.get('order') or 'lastname'

        def key(user: dict[str, Any]) -> tuple[bool, str]:
            text = '' if user[order] is None else str(user[order])
            if order in ('firstname', 'lastname'):
                text = text.casefold()
            return (text == '', unicodedata.normalize('NFKD', text))

        rows.sort(key=key, reverse=params.get('direction') == 'desc')
        offset, limit = params.get('offset', 0), params.get('limit')
        page = rows[offset:] if not limit else rows[offset : offset + limit]
        return {'items': page, 'total': len(rows)}

    def snapshot_loads(self) -> list[dict[str, Any]]:
        return [call for call in self.calls if call == LOAD_PARAMS]

    def listings(self) -> list[dict[str, Any]]:
        return [call for call in self.calls if call != LOAD_PARAMS]

    def searched(self) -> list[dict[str, Any]]:
        return [call for call in self.calls if 'search' in call]
