# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Proformatique, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import sys

from flask import Flask, jsonify
from flask import request

app = Flask(__name__)

port = int(sys.argv[1])

context = ('/usr/local/share/ssl/auth/server.crt',
           '/usr/local/share/ssl/auth/server.key')

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
    for f in context:
        with open(f):
            print 'Success', f
    app.run(host='0.0.0.0', port=port, ssl_context=context, debug=True)
