# -*- coding: utf-8 -*-
# Copyright (C) 2016 Avencall
# SPDX-License-Identifier: GPL-3.0+

import sys

from flask import Flask, jsonify
from flask import request

app = Flask(__name__)

port = int(sys.argv[1])

context = ('/usr/local/share/ssl/auth/server.crt', '/usr/local/share/ssl/auth/server.key')

tokens = {'valid-token': 'uuid',
          'valid-token-1': 'uuid-1',
          'valid-token-2': 'uuid-2'}

tokens_acl = {'valid-token-no-acl': ''}


@app.route("/0.1/token/<token>", methods=['HEAD'])
def token_head(token):
    if token in tokens:
        return '', 204

    if token in tokens_acl:
        if tokens_acl[token] == request.args.get('scope'):
            return '', 204
        return '', 403
    return '', 404


@app.route("/0.1/token/<token>", methods=['GET'])
def token_get(token):
    if token not in tokens:
        return '', 404

    return jsonify({
        'data': {
            'auth_id': tokens[token],
            'token': token,
            'xivo_user_uuid': tokens[token],
        }
    })


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=port, ssl_context=context, debug=True)
