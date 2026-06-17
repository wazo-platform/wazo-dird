# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from wazo_dird import BaseViewPlugin
from wazo_dird.plugin_manager import ViewDependencies

from . import http


class ProfilesViewPlugin(BaseViewPlugin):
    def load(self, dependencies: ViewDependencies) -> None:
        api = dependencies['api']
        profile_service = dependencies['services']['profile']

        api.add_resource(
            http.Profiles, '/profiles', resource_class_args=(profile_service,)
        )

        api.add_resource(
            http.Profile,
            '/profiles/<profile_uuid>',
            resource_class_args=(profile_service,),
        )
