#!/usr/bin/env python3
# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

"""A confd that pages `GET /1.1/users` the way confd does, and counts the calls.

The other confd assets answer a user list with every user and ignore `limit`
and `offset`, so the paging of the user snapshot never runs against them. This
one is opt-in and serves the users that a test sends with `PUT /_state`.

    PUT    /_state   {"users": [...], "ignore_offset": bool, "total": int|null}
    GET    /_stats   {"users_requests": n, "pages": [[limit, offset], ...]}

`PUT /_state` also clears the stats. `ignore_offset` and `total` let a test
build a confd that answers wrongly. The state is kept in a file, so a test
that stops and starts the container finds its users again. A client that sends
more than MAX_USERS_REQUESTS user requests since the last state gets a 503,
which ends a runaway load instead of flooding the container.
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

PORT = 9486
STATE_PATH = '/var/lib/snapshot-confd.json'
MAX_USERS_REQUESTS = 100
INFOS = {'uuid': '6fa459ea-ee8a-3ca4-894e-db77e160snap'}

LOCK = threading.Lock()
STATE: dict[str, Any] = {'users': [], 'ignore_offset': False, 'total': None}
STATS: dict[str, Any] = {'users_requests': 0, 'pages': []}


def _reset_stats() -> None:
    STATS['users_requests'] = 0
    STATS['pages'] = []


def _users(query: dict[str, list[str]]) -> dict[str, Any]:
    users = sorted(STATE['users'], key=lambda user: user['id'])
    if wanted := query.get('uuid'):
        keep = set(wanted[0].split(','))
        users = [user for user in users if user['uuid'] in keep]

    limit = int(query['limit'][0]) if 'limit' in query else None
    offset = int(query['offset'][0]) if 'offset' in query else 0
    STATS['users_requests'] += 1
    STATS['pages'].append([limit, offset])

    start = 0 if STATE['ignore_offset'] else offset
    items = users[start:] if limit is None else users[start : start + limit]
    total = STATE['total'] if STATE['total'] is not None else len(users)
    return {'items': items, 'total': total}


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: Any) -> None:
        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        url = urlparse(self.path)
        with LOCK:
            if url.path == '/1.1/infos':
                self._send(INFOS)
            elif url.path == '/1.1/users':
                if STATS['users_requests'] >= MAX_USERS_REQUESTS:
                    self.send_error(503)
                    return
                self._send(_users(parse_qs(url.query)))
            elif url.path == '/_stats':
                self._send(STATS)
            else:
                self.send_error(404)

    def do_PUT(self) -> None:
        if urlparse(self.path).path != '/_state':
            self.send_error(404)
            return

        length = int(self.headers.get('Content-Length', 0))
        state = json.loads(self.rfile.read(length))
        with LOCK:
            STATE.update(
                users=state['users'],
                ignore_offset=state.get('ignore_offset', False),
                total=state.get('total'),
            )
            with open(STATE_PATH, 'w') as f:
                json.dump(STATE, f)
            _reset_stats()
            self._send({})

    def log_message(self, *args: Any) -> None:
        # the container log is read when a test fails; keep it to the point
        pass


if __name__ == '__main__':
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            STATE.update(json.load(f))
    # threading: a lookup that loads the snapshot and a test that reads the stats
    # reach the mock at the same time
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
