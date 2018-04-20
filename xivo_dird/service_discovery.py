# -*- coding: utf-8 -*-
# Copyright 2016-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import requests


# this function is not executed from the main thread
def self_check(port):
    url = 'https://localhost:{}/0.1/directories/lookup/foobar/headers'.format(port)
    try:
        return requests.get(url, headers={'accept': 'application/json'}, verify=False).status_code == 401
    except Exception:
        return False
