#!/usr/bin/env python3
# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

"""CSV lists by name, counted; /_set/<name> changes a list's size, delay or status."""

import threading
import time

from flask import Flask, Response, jsonify, request

app = Flask(__name__)
lock = threading.Lock()
calls: dict[str, int] = {}
lists: dict[str, dict] = {}


def _settings(name: str) -> dict:
    return lists.setdefault(name, {'size': 2, 'delay': 0.0, 'status': 200})


@app.route('/list/<name>')
def list_(name: str) -> Response:
    with lock:
        calls[name] = calls.get(name, 0) + 1
        settings = dict(_settings(name))
    time.sleep(settings['delay'])
    if settings['status'] != 200:
        return Response('', status=settings['status'])
    rows = ['id,firstname,lastname'] + [
        f'{name}-{i:04d},{name},{i}' for i in range(settings['size'])
    ]
    return Response('\n'.join(rows) + '\n', content_type='text/csv; charset=utf-8')


@app.route('/_set/<name>', methods=['POST'])
def set_(name: str) -> Response:
    with lock:
        _settings(name).update(request.get_json())
    return jsonify(lists[name])


@app.route('/_calls/<name>')
def calls_(name: str) -> Response:
    with lock:
        return jsonify(calls.get(name, 0))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9485, threaded=True)
