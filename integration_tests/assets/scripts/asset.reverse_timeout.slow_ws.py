#!/usr/bin/env python3
# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import time
from collections.abc import Iterator

from flask import Flask, Response

app = Flask(__name__)

DELAY = 2.0
NUMBER = '5551234567'
FIRSTNAME = 'Alice'
LASTNAME = 'Timeout'


@app.route('/ws')
def ws() -> Response:
    time.sleep(DELAY)

    def generate() -> Iterator[str]:
        yield 'number,firstname,lastname\n'
        yield f'{NUMBER},{FIRSTNAME},{LASTNAME}\n'

    return Response(generate(), content_type='text/csv; charset=utf-8')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9485)
