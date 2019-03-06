# Copyright 2015-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later


class BrokenPlugin:

    def __init__(self):
        raise RuntimeError('BROKEN')


class BrokenLookup:

    def load(self, config):
        return

    def search(self, term, args=None):
        raise RuntimeError('This backend is broken')

    def list(self, source_entry_id, args=None):
        raise RuntimeError('This backend is broken')
