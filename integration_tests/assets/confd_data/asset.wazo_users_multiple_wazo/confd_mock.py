#!/usr/bin/env python3
# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

"""Serve the confd routes wazo-dird uses, from the JSON files of one wazo.

`python3 -m http.server` maps a path to a file and drops the query string, so
it answered a filtered request with every user. That hid whether dird sends a
correct `uuid` filter, and left `GET /users/<id>` with nowhere to come from.
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

PORT = 9486
ROOT = sys.argv[1] if len(sys.argv) > 1 else '.'


def _read(name: str) -> Any:
    # the fixtures stay plain JSON files, as the other confd assets keep them
    with open(f'{ROOT}/1.1/{name}') as f:
        return json.load(f)


def _route(parts: list[str], query: dict[str, list[str]]) -> Any:
    match parts:
        case ['1.1', 'infos']:
            return _read('infos')

        case ['1.1', 'users']:
            users = _read('users')
            # `uuid` is the only list filter confd applies itself; dird narrows
            # `search` and the first_matched_columns on its side, so a mock that
            # filtered those too would test the wrong half of the exchange
            if wanted := query.get('uuid'):
                keep = set(wanted[0].split(','))
                items = [user for user in users['items'] if user['uuid'] in keep]
                return {'items': items, 'total': len(items)}
            return users

        case ['1.1', 'users', key]:
            # confd resolves this route by id *or* uuid, and dird relies on both
            return next(
                (
                    user
                    for user in _read('users')['items']
                    if key in (str(user['id']), user.get('uuid'))
                ),
                None,
            )

    return None


class ConfdHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        url = urlparse(self.path)
        try:
            body = _route(url.path.strip('/').split('/'), parse_qs(url.query))
        except FileNotFoundError:
            # a wazo with no `users` file answers 404, which is how the assets
            # that need a failing confd are built
            body = None

        if body is None:
            self.send_error(404)
            return

        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args: Any) -> None:
        # the container log is read when a test fails; keep it to the point
        pass


if __name__ == '__main__':
    # threading: dird queries several sources at once, and one slow answer must
    # not hold up the others
    ThreadingHTTPServer(('0.0.0.0', PORT), ConfdHandler).serve_forever()
