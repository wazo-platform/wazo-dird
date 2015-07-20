# -*- coding: utf-8 -*-
# Copyright (C) 2015 Avencall
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

import base64
import json
import sys

from flask import Flask, make_response, request

app = Flask(__name__)

port = int(sys.argv[1])

kv_store = {}
acl = {'valid-token': 'uuid',
       'valid-token-1': 'uuid-1',
       'valid-token-2': 'uuid-2'}


def get_key(url):
    return url.split('/', 3)[3]


def item(key):
    return {
        "CreateIndex": 1,
        "ModifyIndex": 2,
        "LockIndex": 3,
        "Key": key,
        "Flags": 0,
        "Value": base64.b64encode(kv_store[key]),
        "Session": "a-session"
    }


def truncate_key(key, search_start, last_char):
    try:
        sep_index = key.index(last_char, search_start)
        truncated_key = key[:sep_index+1]
    except ValueError:
        truncated_key = key

    return truncated_key


def response(data, code=200):
    _response = make_response(json.dumps(data), code)
    _response.headers['Content-Type'] = 'application/json'
    _response.headers['X-Consul-Index'] = 2
    return _response


@app.route("/v1/kv/xivo/private/<uuid>/<path:path>", methods=['GET'], strict_slashes=False)
def kv_get(uuid, path):
    if 'token' not in request.args or acl.get(request.args['token']) != uuid:
        return response('', 401)

    root_key = get_key(request.path)
    subkeys = [key for key in kv_store.keys() if key.startswith(root_key)]
    result = []

    if request.args.get('keys', False):
        separator = request.args.get('separator')
        if separator:
            subkeys = set(truncate_key(key, search_start=len(root_key), last_char=separator) for key in subkeys)
        result = list(subkeys)

    if request.args.get('recurse', False):
        result = [item(key) for key in subkeys]

    if root_key in kv_store:
        result = [item(root_key)]

    if result:
        return response(result, 200)

    # Consul prefers None to empty list
    return response(None, 404)


@app.route("/v1/kv/xivo/private/<uuid>/<path:path>", methods=['PUT'])
def kv_put(uuid, path):
    if 'token' not in request.args or acl.get(request.args['token']) != uuid:
        return response('', 401)

    key = get_key(request.path)
    value = request.data
    kv_store[key] = value
    return response('true')


@app.route("/v1/kv/xivo/private/<uuid>/<path:path>", methods=['DELETE'])
def kv_delete(uuid, path):
    if 'token' not in request.args or acl.get(request.args['token']) != uuid:
        return response('', 401)

    request_key = get_key(request.path)

    if request.args.get('recurse', False):
        for key in kv_store.keys():
            if key.startswith(request_key):
                kv_store.pop(key)
        return response('true')

    if request_key in kv_store:
        kv_store.pop(request_key)
        return response('true')

    return response('', 404)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=port, debug=True)
