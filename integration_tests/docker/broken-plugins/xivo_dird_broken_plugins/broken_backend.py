# Copyright (C) 2015 Avencall
# SPDX-License-Identifier: GPL-3.0+


class BrokenPlugin(object):

    def __init__(self):
        raise RuntimeError('BROKEN')


class BrokenLookup(object):

    def load(self, config):
        return

    def search(self, term, args=None):
        raise RuntimeError('This backend is broken')

    def list(self, source_entry_id, args=None):
        raise RuntimeError('This backend is broken')
