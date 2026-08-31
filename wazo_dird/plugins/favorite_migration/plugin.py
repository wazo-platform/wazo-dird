# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import cast

from wazo_dird import BaseViewPlugin
from wazo_dird.plugin_manager import ViewDependencies

from .http import FavoriteMigrationResource
from .service import FavoriteMigrationService, SourceServiceProtocol

# Temporary plugin for the wazo source contact_id migration (confd id -> user uuid).
# It is deliberately absent from the default enabled views: wazo-upgrade enables it
# through conf.d, calls it once, then removes it and restarts wazo-dird.


class FavoriteMigrationViewPlugin(BaseViewPlugin):
    def load(self, dependencies: ViewDependencies) -> None:
        api = dependencies['api']
        source_service = cast(
            'SourceServiceProtocol', dependencies['services']['source']
        )
        service = FavoriteMigrationService(source_service)
        api.add_resource(
            FavoriteMigrationResource,
            '/favorite_migration',
            resource_class_args=(service,),
        )
