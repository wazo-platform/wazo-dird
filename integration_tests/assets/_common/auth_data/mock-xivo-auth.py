import sys

from flask import Flask

app = Flask(__name__)

port = int(sys.argv[1])


@app.route("/0.1/token/valid-token", methods=['HEAD'])
def token_head():
    return '', 204

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=port)
