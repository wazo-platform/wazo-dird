import sys

from flask import Flask, jsonify
from flask import request

app = Flask(__name__)

port = int(sys.argv[1])

context = ('/etc/ssl/server.crt', '/etc/ssl/server.key')

tokens = {'valid-token': 'uuid',
          'valid-token-1': 'uuid-1',
          'valid-token-2': 'uuid-2'}

VALID_ACLS = ['acl:dird.directories.reverse.default.uuid',
              'acl:dird.directories.menu.default.uuid',
              'acl:dird.directories.menu.menu.uuid',
              'acl:dird.directories.input.default.uuid',
              'acl:dird.directories.input.input.uuid',
              'acl:dird.directories.lookup.default.uuid',
              'acl:dird.directories.lookup.quiproquo.uuid',
              ]


@app.route("/0.1/token/valid-token", methods=['HEAD'])
@app.route("/0.1/token/valid-token-1", methods=['HEAD'])
@app.route("/0.1/token/valid-token-2", methods=['HEAD'])
def token_head():
    required_acl = request.args.get('scope', None)
    if required_acl is None:
        return '', 204
    if required_acl in VALID_ACLS:
        return '', 204
    return '', 401


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
