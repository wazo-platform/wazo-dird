#!/usr/bin/env python3
# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
import sys

from flask import Flask, request, Response


app = Flask(__name__)

context = (
    '/usr/local/share/ssl/generic/server.crt',
    '/usr/local/share/ssl/generic/server.key',
)

headers = ['id', 'firstname', 'lastname', 'number']
entries = [
    (1, 'Andrée-Anne', 'Smith', '5551231111'),
    (42, 'Benoît', 'Malone', '5551232222'),
    (3, 'Jack', 'Sparrow', '5551233333'),
]

separator = sys.argv[1]
charset = sys.argv[2]


def line(fields, sep=separator):
    return f'{sep.join(map(str, fields))}\n'.encode(charset)


@app.route('/ws')
def ws():
    result = set()

    if not request.args.keys():
        result = entries

    for field, term in request.args.items():
        if field not in headers:
            continue

        i = headers.index(field)
        for entry in entries:
            if term.lower() in entry[i].lower():
                result.add(entry)

    data = list(result)
    if not data:
        return '', 404

    def generate():
        yield line(headers)
        for entry in data:
            yield line(entry)

    return Response(generate(), content_type=f'text/csv; charset={charset}')


def main():
    app.run(host='0.0.0.0', port=9485, ssl_context=context)


if __name__ == '__main__':
    main()
