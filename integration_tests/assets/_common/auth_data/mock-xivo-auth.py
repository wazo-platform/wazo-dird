import sys

from flask import Flask
from OpenSSL import SSL

app = Flask(__name__)

port = int(sys.argv[1])

context = SSL.Context(SSL.SSLv23_METHOD)
context.use_privatekey_file('/etc/ssl/server.key')
context.use_certificate_file('/etc/ssl/server.crt')


@app.route("/0.1/token/valid-token", methods=['HEAD'])
def token_head():
    return '', 204

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=port, ssl_context=context)
