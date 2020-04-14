# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later


class Resolver:
    def hello(self, root, info, **args):
        return 'world'

    def get_user_me(self, root, info, **args):
        return {}

    def get_user_contacts(self, root, info, **args):
        return [{}, {}]

    def get_contact_firstname(self, root, info, **args):
        return 'paul'
