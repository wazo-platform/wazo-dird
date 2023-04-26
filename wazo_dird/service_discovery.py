# Copyright 2016-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import requests


# this function is not executed from the main thread
def self_check(port):
    url = f'http://localhost:{port}/0.1/status'
    try:
        response = requests.get(url, headers={'accept': 'application/json'})
        return response.status_code == 401
    except Exception:
        return False
