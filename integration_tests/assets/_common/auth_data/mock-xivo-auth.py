# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Avencall
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

context = ('/etc/ssl/server.crt', '/etc/ssl/server.key')

tokens = {'valid-token': 'uuid',
          'valid-token-1': 'uuid-1',
          'valid-token-2': 'uuid-2'}

VALID_ACLS = ['dird.directories.reverse.default.uuid',
              'dird.directories.reverse.default.invalid_uuid',
              'dird.directories.menu.default.uuid',
              'dird.directories.menu.menu.uuid',
              'dird.directories.input.default.uuid',
              'dird.directories.input.input.uuid',
              'dird.directories.lookup.default.uuid',
              'dird.directories.lookup.quiproquo.uuid',
              'dird.directories.lookup.test_fallback.uuid',
              'dird.directories.lookup.test_sorted.uuid',
              ]


@app.route("/0.1/token/valid-token", methods=['HEAD'])
@app.route("/0.1/token/valid-token-1", methods=['HEAD'])
@app.route("/0.1/token/valid-token-2", methods=['HEAD'])
def token_head():
    required_acl = request.args.get('scope')
    if not required_acl:
        return '', 204
    if required_acl in VALID_ACLS:
        return '', 204
    return '', 403


@app.route("/0.1/token/<token>", methods=['GET'])
def token_get(token):
    if token not in tokens:
        return '', 404

    return jsonify({
        'data': {
            'auth_id': tokens[token],
            'token': token,
            'xivo_user_uuid': ''
        }
    })


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=port, ssl_context=context, debug=True)
