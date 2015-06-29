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


def response(data, code=200):
    _response = make_response(json.dumps(data), code)
    _response.headers['Content-Type'] = 'application/json'
    _response.headers['X-Consul-Index'] = 2
    return _response


@app.route("/v1/kv/xivo/private/<uuid>/contacts/favorites/<source>", methods=['GET'])
def kv_list(uuid, source):
    if acl.get(request.args['token'], None) != uuid:
        return response('', 401)

    if request.args.get('keys', False):
        root_key = get_key(request.path)
        keys = [key for key in kv_store.keys() if key.startswith(root_key)]
        return response(keys)

    return response('')


@app.route("/v1/kv/xivo/private/<uuid>/contacts/favorites/<source>/<contact>", methods=['GET'])
def kv_get(uuid, source, contact):
    if acl.get(request.args['token'], None) != uuid:
        return response('', 401)

    key = get_key(request.path)

    if key not in kv_store:
        return response('', 404)

    return response([{
        "CreateIndex": 1,
        "ModifyIndex": 2,
        "LockIndex": 3,
        "Key": key,
        "Flags": 0,
        "Value": base64.b64encode(kv_store[key]),
        "Session": "a-session"
    }])


@app.route("/v1/kv/xivo/private/<uuid>/contacts/favorites/<source>/<contact>", methods=['PUT'])
def kv_put(uuid, source, contact):
    if acl.get(request.args['token'], None) != uuid:
        return response('', 401)

    key = get_key(request.path)
    value = request.data
    kv_store[key] = value
    return response('true')


@app.route("/v1/kv/xivo/private/<uuid>/contacts/favorites/<source>/<contact>", methods=['DELETE'])
def kv_delete(uuid, source, contact):
    if acl.get(request.args['token'], None) != uuid:
        return response('', 401)

    key = get_key(request.path)

    if key not in kv_store:
        return response('', 404)

    kv_store.pop(key)
    return response('true')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=port, debug=True)
